import time
import requests
import random
import re
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Q
from .models import Problem, Comment, CommentRating, UserProfile
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from .vision import check_image_safety as vision_check
from django.core.cache import cache
import base64
import json
import threading


# 1. หน้าแรกปกติ (เรนเดอร์หน้า home.html)
def home_view(request):
    # แก้บัค #2: home_view POST ต้องล็อกอินก่อนถึงสร้าง Problem ได้
    # และต้องผูก reported_by กับ user ที่ล็อกอิน
    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "กรุณาล็อกอินก่อนส่งรายงานปัญหา")
            return redirect("login")

        title = request.POST.get("title", "").strip()
        category = request.POST.get("category", "ROADS")
        description = request.POST.get("description", "").strip()

        if title and description:
            problem = Problem.objects.create(
                title=title,
                category=category,
                description=description,
                reported_by=request.user,  # แก้: เพิ่ม reported_by
            )
            notify_admin_new_problem(problem)
            messages.success(
                request, "ส่งรายงานปัญหาเรียบร้อยแล้ว รอการตรวจสอบจากแอดมิน"
            )
            return redirect("home")
        else:
            messages.error(request, "กรุณากรอกหัวข้อและรายละเอียดให้ครบถ้วน")

    total_problems = Problem.objects.filter(is_approved=True).count()
    progress_problems = Problem.objects.filter(
        is_approved=True, status="PROGRESS"
    ).count()
    completed_problems = Problem.objects.filter(
        is_approved=True, status="COMPLETED"
    ).count()
    recent_problems = Problem.objects.filter(is_approved=True).order_by("-created_at")[
        :5
    ]

    context = {
        "recent_problems": recent_problems,
        "total_problems": total_problems,
        "progress_problems": progress_problems,
        "completed_problems": completed_problems,
    }
    return render(request, "home.html", context)


# 2. API จ่ายข้อมูลดิบไปพล็อตกราฟ (ส่งข้อมูลเป็น JSON)
def problem_chart_data(request):
    data_query = (
        Problem.objects.filter(is_approved=True)
        .values("category")
        .annotate(total=Count("id"))
    )

    labels = []
    values = []

    category_map = dict(Problem.CATEGORY_CHOICES)

    for item in data_query:
        labels.append(category_map.get(item["category"], item["category"]))
        values.append(item["total"])

    return JsonResponse({"labels": labels, "data": values})


def search(request):
    q = request.GET.get("q", "")
    results = Problem.objects.filter(title__icontains=q)
    # แก้บัค #9: ใช้ propose_solutions.html แทน search.html ที่ไม่มี
    return render(request, "propose_solutions.html", {"problems": results, "query": q})


@login_required(login_url="login")
def propose_solution(request):
    problems = Problem.objects.filter(is_approved=True).order_by("-created_at")

    tag = request.GET.get("tag", "").strip()
    if tag:
        problems = problems.filter(tags__icontains=tag)

    category = request.GET.get("category", "").strip()
    if category:
        problems = problems.filter(category=category)

    return render(request, "propose_solutions.html", {"problems": problems})


def favicon(request):
    favicon_png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAKbYBvgAAAAASUVORK5CYII="
    )
    return HttpResponse(favicon_png, content_type="image/png")


def problem_detail_public(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    comments = Comment.objects.filter(problem=problem, parent=None).order_by(
        "created_at"
    )
    return render(
        request,
        "problem_detail.html",
        {
            "problem": problem,
            "comments": comments,
            "stars": range(1, 6),
        },
    )


def graph(request):
    return render(request, "graph.html")


def logout(request):
    auth_logout(request)
    return redirect("home")


def sign_up(request):
    context = {"RECAPTCHA_SITE_KEY": settings.RECAPTCHA_SITE_KEY}

    if request.method == "POST":
        if not settings.RECAPTCHA_SITE_KEY or settings.RECAPTCHA_SITE_KEY.startswith(
            "YOUR_"
        ):
            messages.error(request, "reCAPTCHA ยังไม่ได้ตั้งค่า")
            return render(request, "sign_up.html", context)

        token = request.POST.get("g-recaptcha-response", "")
        if not token:
            messages.error(request, "กรุณายืนยัน reCAPTCHA ก่อนสมัคร")
            return render(request, "sign_up.html", context)

        try:
            response = requests.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={
                    "secret": settings.RECAPTCHA_SECRET_KEY,
                    "response": token,
                    "remoteip": request.META.get("REMOTE_ADDR", ""),
                },
                timeout=5,
            )
            result = response.json() if response.ok else {}
        except requests.RequestException:
            messages.error(request, "ไม่สามารถยืนยัน reCAPTCHA ได้ กรุณาลองใหม่")
            return render(request, "sign_up.html", context)

        if not result.get("success"):
            messages.error(request, "reCAPTCHA ไม่ผ่าน กรุณาลองใหม่")
            return render(request, "sign_up.html", context)

        student_id = request.POST.get("student_id", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        faculty = request.POST.get("faculty", "").strip()

        if not student_id or not email or not password or not faculty:
            messages.error(request, "กรุณากรอกข้อมูลทุกช่องให้ครบถ้วน")
            return render(request, "sign_up.html", context)
        ALLOWED_DOMAINS = ["student.chula.ac.th", "chula.ac.th"]
        email_domain = email.split("@")[-1].lower()
        if email_domain not in ALLOWED_DOMAINS:
            messages.error(
                request,
                "กรุณาใช้อีเมลของจุฬาลงกรณ์มหาวิทยาลัยเท่านั้น (@student.chula.ac.th หรือ @chula.ac.th)",
            )
            return render(request, "sign_up.html", context)

        pw = password or ""
        if (
            len(pw) < 8
            or not re.search(r"[A-Z]", pw)
            or not re.search(r"[a-z]", pw)
            or not re.search(r"[0-9]", pw)
            or not re.search(r"[^A-Za-z0-9]", pw)
        ):
            messages.error(
                request,
                "รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร และประกอบด้วย ตัวพิมพ์ใหญ่ ตัวพิมพ์เล็ก ตัวเลข และอักขระพิเศษ",
            )
            return render(request, "sign_up.html", context)

        if User.objects.filter(username=student_id).exists():
            messages.error(request, "Student ID นี้ถูกใช้งานแล้ว")
            return render(request, "sign_up.html", context)

        if User.objects.filter(email=email).exists():
            messages.error(request, "อีเมลนี้ถูกใช้งานแล้ว")
            return render(request, "sign_up.html", context)

        user = User.objects.create_user(
            username=student_id,
            email=email,
            password=password,
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.faculty = faculty
        profile.save()
        auth_login(request, user)
        messages.success(request, "สมัครสมาชิกสำเร็จ และล็อกอินเข้าสู่ระบบแล้ว")
        return redirect("profile")

    return render(request, "sign_up.html", context)


def send_otp_email(subject, message, from_email, recipient_list):
    """ส่งเมลใน background thread เพื่อไม่ให้ block request"""

    def _send():
        try:
            send_mail(subject, message, from_email, recipient_list, fail_silently=True)
        except Exception:
            pass

    threading.Thread(target=_send, daemon=True).start()


def notify_admin_new_problem(problem):
    """แจ้งแอดมินเมื่อมีปัญหาใหม่รออนุมัติ"""
    admin_email = getattr(settings, "ADMIN_NOTIFY_EMAIL", "")
    if not admin_email:
        return
    send_otp_email(
        subject=f"[CoSolvers] มีปัญหาใหม่รออนุมัติ: {problem.title}",
        message=(
            f"มีผู้ใช้รายงานปัญหาใหม่: {problem.title}\n"
            f"หมวดหมู่: {problem.get_category_display()}\n"
            f"ผู้รายงาน: {problem.reported_by}\n\n"
            f"กรุณาเข้าไปตรวจสอบและอนุมัติที่หน้า Admin (/admin/viable_graph_app/problem/)"
        ),
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[admin_email],
    )


@login_required(login_url="login")
def profile(request):
    my_problems = Problem.objects.filter(reported_by=request.user)

    # ข้อเสนอแนวทางแก้ปัญหาของฉัน = คอมเมนต์ที่ user คนนี้เคยเขียนไว้ในปัญหาต่างๆ
    my_comments = (
        Comment.objects.filter(author=request.user)
        .select_related("problem")
        .order_by("-created_at")
    )
    my_purposes = [
        {
            "title": c.problem.title if c.problem else "",
            "comment": c.text,
            "rating": c.rating,  # ค่าเฉลี่ยดาวที่คนอื่นให้คอมเมนต์นี้ (property จาก model)
        }
        for c in my_comments
    ]

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile_photo = profile.photo.url if profile.photo else None

    return render(
        request,
        "profile.html",
        {
            "my_problems": my_problems,
            "score": 0,
            "my_purposes": my_purposes,
            "profile_photo": profile_photo,
            "stars": range(1, 6),
        },
    )


@login_required(login_url="login")
def upload_photo(request):
    """อัปโหลดรูปโปรไฟล์ — ตรวจสอบด้วย Google Vision ก่อนบันทึก"""
    if request.method == "POST" and request.FILES.get("photo"):
        photo = request.FILES["photo"]

        result = vision_check(photo)
        if not result["safe"]:
            return JsonResponse({"success": False, "reason": result["reason"]})

        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.photo = photo
        profile.save()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "reason": "ไม่พบไฟล์ภาพ"})


@login_required(login_url="login")
def define_problem(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        category = request.POST.get("category", "WASTE")
        description = request.POST.get("description", "").strip()
        location = request.POST.get("location", "").strip()
        tags = request.POST.get("tags", "").strip()
        incident_date = request.POST.get("incident_date") or None
        photo = request.FILES.get("photo")

        if not title:
            messages.error(request, "กรุณากรอกชื่อปัญหา")
            return render(request, "define_problem.html")

        # ตรวจสอบรูปภาพด้วย Google Vision API (server-side)
        if photo:
            vision_result = vision_check(photo)
            if not vision_result["safe"]:
                messages.error(
                    request, f"❌ {vision_result['reason']} กรุณาเลือกรูปอื่น"
                )
                return render(request, "define_problem.html")

        problem = Problem.objects.create(
            title=title,
            category=category,
            description=description,
            location=location,
            tags=tags,
            incident_date=incident_date,
            photo=photo,
            reported_by=request.user,
        )
        notify_admin_new_problem(problem)
        messages.success(request, "ส่งรายงานปัญหาเรียบร้อยแล้ว รอการตรวจสอบจากแอดมิน")
        return redirect("home")

    return render(request, "define_problem.html")


# แก้บัค #1: รวม problem_detail ให้ใช้ view เดียวกับ problem_detail_public
# เพื่อไม่ให้ redirect loop และ 404 สำหรับคนที่ไม่ใช่เจ้าของ
@login_required(login_url="login")
def problem_detail(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    comments = Comment.objects.filter(problem=problem, parent=None).order_by(
        "created_at"
    )
    return render(
        request,
        "problem_detail.html",
        {
            "problem": problem,
            "comments": comments,
            "stars": range(1, 6),
        },
    )


@login_required(login_url="login")
def add_comment(request, problem_id):
    if request.method == "POST":
        problem = get_object_or_404(Problem, id=problem_id)
        text = request.POST.get("text", "").strip()
        parent_id = request.POST.get("parent_id")
        if text:
            Comment.objects.create(
                problem=problem,
                author=request.user,
                text=text,
                parent_id=parent_id or None,
            )
    return redirect("problem_detail_public", problem_id=problem_id)


@login_required(login_url="login")
def rate_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if request.method == "POST":
        if comment.author == request.user:
            messages.error(request, "คุณไม่สามารถให้คะแนนคอมเมนต์ของตัวเองได้")
            return redirect(
                "problem_detail_public", problem_id=getattr(comment.problem, "id", None)
            )
        try:
            rating = int(request.POST.get("rating", 0))
        except (TypeError, ValueError):
            rating = 0
        if 1 <= rating <= 5:
            CommentRating.objects.update_or_create(
                comment=comment,
                user=request.user,
                defaults={"rating": rating},
            )
    return redirect(
        "problem_detail_public", problem_id=getattr(comment.problem, "id", None)
    )


@login_required(login_url="login")
def report_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if request.method == "POST":
        comment.is_reported = True
        comment.save()
    return redirect(
        "problem_detail_public", problem_id=getattr(comment.problem, "id", None)
    )


@login_required(login_url="login")
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if request.method == "POST" and comment.author == request.user:
        problem_id = getattr(comment.problem, "id", None)
        comment.delete()
        return redirect("problem_detail_public", problem_id=problem_id)
    return redirect(
        "problem_detail_public", problem_id=getattr(comment.problem, "id", None)
    )


@login_required(login_url="login")
def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if comment.author != request.user:
        messages.error(request, "คุณไม่มีสิทธิ์แก้ไขคอมเมนต์นี้")
        return redirect(
            "problem_detail_public", problem_id=getattr(comment.problem, "id", None)
        )
    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        if text:
            comment.text = text
            comment.save()
    return redirect(
        "problem_detail_public", problem_id=getattr(comment.problem, "id", None)
    )


# แก้บัค #6: about_us ใช้ home.html แทนเพราะไม่มี about_us.html
# ถ้าอยากทำหน้า About Us จริงๆ ค่อยสร้าง template เพิ่ม
def about_us(request):
    return redirect("home")


OTP_EXPIRY_SECONDS = 300  # 5 นาที


def reset_pass(request):
    if request.method == "POST":

        if request.POST.get("resend") == "1":
            otp = str(random.randint(100000, 999999))
            request.session["reset_otp"] = otp
            request.session["reset_otp_time"] = time.time()
            email = request.session.get("reset_email", "")
            if email:
                # try:
                send_otp_email(
                    subject="OTP รีเซ็ตรหัสผ่าน",
                    message=f"รหัส OTP ของคุณคือ: {otp}\nหมดอายุใน 5 นาที",
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[email],
                    # fail_silently=False,
                )
            # except Exception as e:
            # return JsonResponse({"status": "error", "message": str(e)})
            return JsonResponse({"status": "sent"})

        student_id = request.POST.get("student_id", "").strip()
        if student_id and not request.POST.get("otp"):
            try:
                user = User.objects.get(username=student_id)
                otp = str(random.randint(100000, 999999))
                request.session["reset_otp"] = otp
                request.session["reset_otp_time"] = time.time()
                request.session["reset_user_id"] = user.pk
                request.session["reset_email"] = user.email
                request.session.save()
                try:
                    send_otp_email(
                        subject="OTP รีเซ็ตรหัสผ่าน",
                        message=f"รหัส OTP ของคุณคือ: {otp}\nหมดอายุใน 5 นาที",
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[user.email],
                    )
                    messages.success(request, f"ส่ง OTP ไปที่ {user.email} แล้ว")
                except Exception as e:
                    messages.error(request, f"ส่ง email ไม่สำเร็จ: {str(e)}")
            except User.DoesNotExist:
                messages.error(request, "ไม่พบ Student ID นี้ในระบบ")
            return render(request, "reset_pass.html")

        otp_input = request.POST.get("otp", "").strip()
        new_password = request.POST.get("new_password", "")
        session_otp = request.session.get("reset_otp", "")
        otp_time = request.session.get("reset_otp_time", 0)
        user_id = request.session.get("reset_user_id")

        if not otp_input or not new_password:
            messages.error(request, "กรุณากรอก OTP และรหัสผ่านใหม่")
            return render(request, "reset_pass.html")

        if time.time() - otp_time > OTP_EXPIRY_SECONDS:
            messages.error(request, "OTP หมดอายุแล้ว กรุณาขอ OTP ใหม่")
            return render(request, "reset_pass.html")

        if otp_input != session_otp:
            messages.error(request, "OTP ไม่ถูกต้อง กรุณาลองใหม่")
            return render(request, "reset_pass.html")

        try:
            user = User.objects.get(id=user_id)
            user.set_password(new_password)
            user.save()
            for key in ["reset_otp", "reset_user_id", "reset_email", "reset_otp_time"]:
                request.session.pop(key, None)
            messages.success(request, "เปลี่ยนรหัสผ่านสำเร็จ กรุณาล็อกอินใหม่")
            return redirect("login")
        except User.DoesNotExist:
            messages.error(request, "เกิดข้อผิดพลาด กรุณาลองใหม่")

    return render(request, "reset_pass.html")


def login(request):
    context = {"RECAPTCHA_SITE_KEY": settings.RECAPTCHA_SITE_KEY}

    if not settings.RECAPTCHA_SITE_KEY or settings.RECAPTCHA_SITE_KEY.startswith(
        "YOUR_"
    ):
        messages.error(request, "reCAPTCHA ยังไม่ได้ตั้งค่า")
        return render(request, "login.html", context)

    if request.method == "POST":
        token = request.POST.get("g-recaptcha-response", "")
        if not token:
            messages.error(request, "กรุณายืนยัน reCAPTCHA ก่อน")
            return render(request, "login.html", context)

        try:
            response = requests.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={
                    "secret": settings.RECAPTCHA_SECRET_KEY,
                    "response": token,
                    "remoteip": request.META.get("REMOTE_ADDR", ""),
                },
                timeout=5,
            )
            result = response.json() if response.ok else {}
        except requests.RequestException:
            messages.error(request, "ไม่สามารถยืนยัน reCAPTCHA ได้ กรุณาลองใหม่")
            return render(request, "login.html", context)

        if not result.get("success"):
            messages.error(request, "reCAPTCHA ไม่ผ่าน กรุณาลองใหม่")
            return render(request, "login.html", context)

        student_id = request.POST.get("student_id", "").strip()
        password = request.POST.get("password", "")

        if not student_id or not password:
            messages.error(request, "กรุณากรอก Student ID และรหัสผ่าน")
            return render(request, "login.html", context)

        user = authenticate(request, username=student_id, password=password)

        if user is not None:
            auth_login(request, user)
            return redirect("profile")
        else:
            messages.error(request, "Student ID หรือรหัสผ่านไม่ถูกต้อง")
            return render(request, "login.html", context)

    return render(request, "login.html", context)


@login_required(login_url="login")
def check_image_safety(request):
    """API endpoint ตรวจสอบความปลอดภัยของรูปก่อนแสดง preview (เรียกจาก JS)"""
    if request.method != "POST":
        return JsonResponse({"safe": False, "reason": "Method not allowed"}, status=405)

    photo = request.FILES.get("photo")
    if not photo:
        return JsonResponse({"safe": False, "reason": "ไม่พบไฟล์ภาพ"}, status=400)

    result = vision_check(photo)
    return JsonResponse({"safe": result["safe"], "reason": result["reason"]})


@login_required(login_url="login")
def edit_problem(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id, reported_by=request.user)

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        category = request.POST.get("category", problem.category)
        description = request.POST.get("description", "").strip()
        location = request.POST.get("location", "").strip()
        tags = request.POST.get("tags", "").strip()
        incident_date = request.POST.get("incident_date") or None
        photo = request.FILES.get("photo")

        if not title:
            messages.error(request, "กรุณากรอกชื่อปัญหา")
            return render(request, "edit_problem.html", {"problem": problem})

        # ตรวจสอบรูปภาพใหม่ด้วย Google Vision API (server-side)
        if photo:
            vision_result = vision_check(photo)
            if not vision_result["safe"]:
                messages.error(
                    request, f"❌ {vision_result['reason']} กรุณาเลือกรูปอื่น"
                )
                return render(request, "edit_problem.html", {"problem": problem})

        problem.title = title
        problem.category = category
        problem.description = description
        problem.location = location
        problem.tags = tags
        problem.incident_date = incident_date
        if photo:
            problem.photo = photo
        problem.save()

        return redirect(f"/problem/public/{getattr(problem, 'id', '')}/?updated=1")

    return render(request, "edit_problem.html", {"problem": problem})


@login_required(login_url="login")
def delete_problem(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id, reported_by=request.user)

    if request.method == "POST":
        problem.delete()
        messages.success(request, "ลบปัญหาเรียบร้อยแล้ว")
        return redirect("profile")

    return redirect("problem_detail_public", problem_id=problem_id)


def solution_chart_data(request):
    category_name = request.GET.get("category", "")

    # แปลงชื่อภาษาไทยกลับเป็น key
    category_map = {v: k for k, v in dict(Problem.CATEGORY_CHOICES).items()}
    category_key = category_map.get(category_name, "")

    # นับ comments แยกตามปัญหาในหมวดนั้น
    problems = Problem.objects.filter(category=category_key)
    data = []
    for p in problems:
        count = Comment.objects.filter(problem=p).count()
        if count > 0:
            data.append({"label": p.title, "val": count})

    # ถ้ายังไม่มี comment ให้แสดงปัญหาทั้งหมดในหมวดนั้น
    if not data:
        for p in problems:
            data.append({"label": p.title, "val": 0})

    data.sort(key=lambda x: x["val"], reverse=True)

    return JsonResponse(
        {
            "labels": [d["label"] for d in data],
            "data": [d["val"] for d in data],
        }
    )


def problems_ranked(request):
    """ส่งรายชื่อปัญหาทั้งหมดเรียงตามจำนวน comment"""
    problems = (
        Problem.objects.filter(is_approved=True)
        .annotate(comment_count=Count("comments"))
        .order_by("-comment_count")
    )
    return JsonResponse(
        {
            "problems": [
                {
                    "id": getattr(p, "id", None),
                    "title": p.title,
                    "count": getattr(p, "comment_count", 0),
                }
                for p in problems
            ]
        }
    )


def problems_by_category(request):
    """ส่งรายชื่อปัญหาในหมวดหมู่ที่ระบุ (รับชื่อหมวดหมู่ภาษาไทย) พร้อมจำนวนวิธีแก้ (comment) ของแต่ละปัญหา"""
    category_name = request.GET.get("category", "")

    # แปลงชื่อภาษาไทยกลับเป็น key เช่นเดียวกับ solution_chart_data
    category_map = {v: k for k, v in dict(Problem.CATEGORY_CHOICES).items()}
    category_key = category_map.get(category_name, "")

    problems = (
        Problem.objects.filter(is_approved=True, category=category_key)
        .annotate(comment_count=Count("comments"))
        .order_by("-comment_count")
    )

    return JsonResponse(
        {
            "problems": [
                {
                    "id": getattr(p, "id", None),
                    "title": p.title,
                    "count": getattr(p, "comment_count", 0),
                }
                for p in problems
            ]
        }
    )


def problem_solutions_data(request):
    problem_id = request.GET.get("problem_id", "")
    try:
        problem = Problem.objects.get(id=problem_id)
    except Problem.DoesNotExist:
        return JsonResponse({"labels": [], "data": [], "details": []})

    # ดึงจาก cache ก่อน (เก็บไว้ 10 นาที)
    from django.core.cache import cache

    cache_key = f"solutions_grouped_{problem_id}"
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)

    comments = list(
        Comment.objects.filter(problem=problem, parent=None).order_by("-rating")
    )

    if not comments:
        return JsonResponse({"labels": [], "data": [], "details": []})

    # ── จัดกลุ่มด้วย clustering module ──
    from . import clustering

    groups = clustering.cluster_comments(comments)

    labels = [g["short_label"] for g in groups]
    data = [g["bar_value"] for g in groups]
    details = [
        {
            "text": g["representative"],
            "rating": g["total_rating"],
            "count": g["count"],
            "members": g["members"],
        }
        for g in groups
    ]

    result = {"labels": labels, "data": data, "details": details}
    cache.set(cache_key, result, timeout=600)
    return JsonResponse(result)
