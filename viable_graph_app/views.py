import requests
import random
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Count
from .models import Problem
from django.conf import settings
from django.core.mail import send_mail


# 1. หน้าแรกปกติ (เรนเดอร์หน้า home.html)
def home_view(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        category = request.POST.get("category", "ROADS")
        description = request.POST.get("description", "").strip()

        if title and description:
            Problem.objects.create(
                title=title, category=category, description=description
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
    # ไปนับจำนวนปัญหาแยกตามหมวดหมู่ในฐานข้อมูล
    data_query = Problem.objects.values("category").annotate(total=Count("id"))

    # จัดโครงสร้างข้อมูลให้อ่านง่ายสำหรับ Frontend
    labels = []
    values = []

    # แปลงชื่อย่อฐานข้อมูลเป็นภาษาไทยก่อนส่งออกไป
    category_map = dict(Problem.CATEGORY_CHOICES)

    for item in data_query:
        labels.append(category_map.get(item["category"], item["category"]))
        values.append(item["total"])

    return JsonResponse({"labels": labels, "data": values})


def search(request):
    q = request.GET.get("q", "")
    results = Problem.objects.filter(title__icontains=q)
    return render(request, "search.html", {"results": results, "query": q})


def propose_solution(request):
    return render(request, "propose_solutions.html")


def graph(request):
    return render(request, "graph.html")


def logout(request):
    auth_logout(request)
    return redirect("home")


def sign_up(request):
    return render(request, "sign_up.html")


def about_us(request):
    return render(request, "about_us.html")


def define_problem(request):
    return render(request, "define_problem.html")


def profile(request):
    return render(request, "profile.html")


def propose_solutions(request):
    return render(request, "propose_solutions.html")


def propose_solutions_2(request):
    return render(request, "propose_solutions_2.html")


def reset_pass(request):
    if request.method == "POST":

        # กรณีกด Resend OTP
        if request.POST.get("resend") == "1":
            otp = str(random.randint(100000, 999999))
            request.session["reset_otp"] = otp
            email = request.session.get("reset_email", "")
            if email:
                send_mail(
                    subject="OTP รีเซ็ตรหัสผ่าน",
                    message=f"รหัส OTP ของคุณคือ: {otp}",
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
                request.session["reset_user_id"] = user.id
                request.session["reset_email"] = user.email
                send_mail(
                    subject="OTP รีเซ็ตรหัสผ่าน",
                    message=f"รหัส OTP ของคุณคือ: {otp}\nหมดอายุใน 5 นาที",
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[user.email],
                )
                messages.success(request, f"ส่ง OTP ไปที่อีเมลแล้ว")
            except User.DoesNotExist:
                messages.error(request, "ไม่พบ Student ID นี้ในระบบ")
            return render(request, "reset_pass.html")

        # กรณีกรอก OTP + รหัสผ่านใหม่
        otp_input = request.POST.get("otp", "").strip()
        new_password = request.POST.get("new_password", "")
        session_otp = request.session.get("reset_otp", "")
        user_id = request.session.get("reset_user_id")

        if not otp_input or not new_password:
            messages.error(request, "กรุณากรอก OTP และรหัสผ่านใหม่")
            return render(request, "reset_pass.html")

        if otp_input != session_otp:
            messages.error(request, "OTP ไม่ถูกต้อง กรุณาลองใหม่")
            return render(request, "reset_pass.html")

        try:
            user = User.objects.get(id=user_id)
            user.set_password(new_password)
            user.save()
            # ล้าง session
            del request.session["reset_otp"]
            del request.session["reset_user_id"]
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
        # 1. ตรวจ reCAPTCHA ก่อน
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

        # 2. ✅ ตรวจ student_id / password จริง ๆ
        student_id = request.POST.get("student_id", "").strip()
        password = request.POST.get("password", "")

        if not student_id or not password:
            messages.error(request, "กรุณากรอก Student ID และรหัสผ่าน")
            return render(request, "login.html", context)

        user = authenticate(request, username=student_id, password=password)

        if user is not None:
            auth_login(request, user)
            return redirect("home")
        else:
            messages.error(request, "Student ID หรือรหัสผ่านไม่ถูกต้อง")
            return render(request, "login.html", context)

    return render(request, "login.html", context)
