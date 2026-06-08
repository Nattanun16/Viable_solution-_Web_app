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
from .models import Problem, Comment, UserProfile
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
import base64
import json


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
            Problem.objects.create(
                title=title,
                category=category,
                description=description,
                reported_by=request.user,  # แก้: เพิ่ม reported_by
            )
            messages.success(request, "ส่งรายงานปัญหาเรียบร้อยแล้ว")
            return redirect("home")
        else:
            messages.error(request, "กรุณากรอกหัวข้อและรายละเอียดให้ครบถ้วน")

    total_problems = Problem.objects.count()
    progress_problems = Problem.objects.filter(status="PROGRESS").count()
    completed_problems = Problem.objects.filter(status="COMPLETED").count()
    recent_problems = Problem.objects.all().order_by("-created_at")[:5]

    context = {
        "recent_problems": recent_problems,
        "total_problems": total_problems,
        "progress_problems": progress_problems,
        "completed_problems": completed_problems,
    }
    return render(request, "home.html", context)


# 2. API จ่ายข้อมูลดิบไปพล็อตกราฟ (ส่งข้อมูลเป็น JSON)
def problem_chart_data(request):
    data_query = Problem.objects.values("category").annotate(total=Count("id"))

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


def propose_solution(request):
    problems = Problem.objects.all().order_by("-created_at")

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
    comments = problem.comments.filter(parent=None).order_by("created_at")
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


@login_required(login_url="login")
def profile(request):
    my_problems = Problem.objects.filter(reported_by=request.user)

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile_photo = profile.photo.url if profile.photo else None

    return render(
        request,
        "profile.html",
        {
            "my_problems": my_problems,
            "score": 0,
            "my_purposes": [],
            "profile_photo": profile_photo,
            "stars": range(1, 6),
        },
    )


@login_required(login_url="login")
def upload_photo(request):
    if request.method == "POST" and request.FILES.get("photo"):
        photo = request.FILES["photo"]

        api_key = getattr(settings, "GOOGLE_VISION_API_KEY", "")
        if api_key and not api_key.startswith("YOUR_"):
            image_data = base64.b64encode(photo.read()).decode("utf-8")
            photo.seek(0)

            vision_url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
            payload = {
                "requests": [
                    {
                        "image": {"content": image_data},
                        "features": [{"type": "SAFE_SEARCH_DETECTION"}],
                    }
                ]
            }
            try:
                vision_response = requests.post(vision_url, json=payload, timeout=10)
                result = vision_response.json()
                annotations = result.get("responses", [{}])[0].get("safeSearchAnnotation", {})
                UNSAFE_LEVELS = {"LIKELY", "VERY_LIKELY"}
                CHECKS = {
                    "adult": "เนื้อหาลามกอนาจาร",
                    "violence": "เนื้อหาที่มีความรุนแรง",
                    "racy": "เนื้อหาไม่เหมาะสม",
                    "medical": "เนื้อหาทางการแพทย์ที่รุนแรง",
                }
                for field, label in CHECKS.items():
                    if annotations.get(field, "UNKNOWN") in UNSAFE_LEVELS:
                        return JsonResponse({"success": False, "reason": f"ภาพถูกปฏิเสธ: พบ{label}"})
            except Exception:
                pass

        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.photo = photo
        profile.save()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False})


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

        Problem.objects.create(
            title=title,
            category=category,
            description=description,
            location=location,
            tags=tags,
            incident_date=incident_date,
            photo=photo,
            reported_by=request.user,
        )
        messages.success(request, "ส่งรายงานปัญหาเรียบร้อยแล้ว")
        return redirect("home")

    return render(request, "define_problem.html")


# แก้บัค #1: รวม problem_detail ให้ใช้ view เดียวกับ problem_detail_public
# เพื่อไม่ให้ redirect loop และ 404 สำหรับคนที่ไม่ใช่เจ้าของ
@login_required(login_url="login")
def problem_detail(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    comments = problem.comments.filter(parent=None).order_by("created_at")
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
    if request.method == "POST":
        comment = get_object_or_404(Comment, id=comment_id)
        rating = int(request.POST.get("rating", 0))
        if 1 <= rating <= 5:
            comment.rating = rating
            comment.save()
        return redirect("problem_detail_public", problem_id=comment.problem.id)


@login_required(login_url="login")
def report_comment(request, comment_id):
    if request.method == "POST":
        comment = get_object_or_404(Comment, id=comment_id)
        comment.is_reported = True
        comment.save()
        return redirect("problem_detail_public", problem_id=comment.problem.id)


@login_required(login_url="login")
def delete_comment(request, comment_id):
    if request.method == "POST":
        comment = get_object_or_404(Comment, id=comment_id, author=request.user)
        problem_id = comment.problem.id
        comment.delete()
        return redirect("problem_detail_public", problem_id=problem_id)


# แก้บัค #6: about_us ใช้ home.html แทนเพราะไม่มี about_us.html
# ถ้าอยากทำหน้า About Us จริงๆ ค่อยสร้าง template เพิ่ม
def about_us(request):
    return redirect("home")


OTP_EXPIRY_SECONDS = 300  # 5 นาที


def reset_pass(request):
    if request.method == "POST":

        # กรณีกด Resend OTP
        if request.POST.get("resend") == "1":
            otp = str(random.randint(100000, 999999))
            request.session["reset_otp"] = otp
            request.session["reset_otp_time"] = time.time()  # แก้บัค #3: บันทึกเวลา
            email = request.session.get("reset_email", "")
            if email:
                send_mail(
                    subject="OTP รีเซ็ตรหัสผ่าน",
                    message=f"รหัส OTP ของคุณคือ: {otp}\nหมดอายุใน 5 นาที",
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[email],
                )
            return JsonResponse({"status": "sent"})

        # กรณีกรอก Student ID เพื่อขอ OTP
        student_id = request.POST.get("student_id", "").strip()
        if student_id and not request.POST.get("otp"):
            try:
                user = User.objects.get(username=student_id)
                otp = str(random.randint(100000, 999999))
                request.session["reset_otp"] = otp
                request.session["reset_otp_time"] = time.time()  # แก้บัค #3: บันทึกเวลา
                request.session["reset_user_id"] = user.id
                request.session["reset_email"] = user.email
                send_mail(
                    subject="OTP รีเซ็ตรหัสผ่าน",
                    message=f"รหัส OTP ของคุณคือ: {otp}\nหมดอายุใน 5 นาที",
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[user.email],
                )
                messages.success(request, "ส่ง OTP ไปที่อีเมลแล้ว")
            except User.DoesNotExist:
                messages.error(request, "ไม่พบ Student ID นี้ในระบบ")
            return render(request, "reset_pass.html")

        # กรณีกรอก OTP + รหัสผ่านใหม่
        otp_input = request.POST.get("otp", "").strip()
        new_password = request.POST.get("new_password", "")
        session_otp = request.session.get("reset_otp", "")
        otp_time = request.session.get("reset_otp_time", 0)
        user_id = request.session.get("reset_user_id")

        if not otp_input or not new_password:
            messages.error(request, "กรุณากรอก OTP และรหัสผ่านใหม่")
            return render(request, "reset_pass.html")

        # แก้บัค #3: ตรวจสอบว่า OTP หมดอายุหรือยัง
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
            # แก้บัค #4: ล้าง session ให้ครบทุก key
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
    if request.method != "POST":
        return JsonResponse({"safe": False, "reason": "Method not allowed"}, status=405)

    photo = request.FILES.get("photo")
    if not photo:
        return JsonResponse({"safe": False, "reason": "ไม่พบไฟล์ภาพ"}, status=400)

    image_data = base64.b64encode(photo.read()).decode("utf-8")

    api_key = settings.GOOGLE_VISION_API_KEY
    if not api_key or api_key.startswith("YOUR_"):
        return JsonResponse({"safe": True, "reason": ""})

    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
    payload = {
        "requests": [
            {
                "image": {"content": image_data},
                "features": [{"type": "SAFE_SEARCH_DETECTION"}],
            }
        ]
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
    except requests.RequestException as e:
        return JsonResponse({"safe": True, "reason": ""})

    annotations = result.get("responses", [{}])[0].get("safeSearchAnnotation", {})

    UNSAFE_LEVELS = {"LIKELY", "VERY_LIKELY"}
    CHECKS = {
        "adult": "เนื้อหาลามกอนาจาร",
        "violence": "เนื้อหาที่มีความรุนแรง",
        "racy": "เนื้อหาไม่เหมาะสม",
        "medical": "เนื้อหาทางการแพทย์ที่รุนแรง",
    }

    for field, label in CHECKS.items():
        if annotations.get(field, "UNKNOWN") in UNSAFE_LEVELS:
            return JsonResponse({"safe": False, "reason": f"ภาพถูกปฏิเสธ: พบ{label}"})

    return JsonResponse({"safe": True, "reason": ""})


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

        problem.title = title
        problem.category = category
        problem.description = description
        problem.location = location
        problem.tags = tags
        problem.incident_date = incident_date
        if photo:
            problem.photo = photo
        problem.save()

        return redirect(f"/problem/public/{problem.id}/?updated=1")

    return render(request, "edit_problem.html", {"problem": problem})


@login_required(login_url="login")
def delete_problem(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id, reported_by=request.user)

    if request.method == "POST":
        problem.delete()
        messages.success(request, "ลบปัญหาเรียบร้อยแล้ว")
        return redirect("profile")

    return redirect("problem_detail_public", problem_id=problem_id)