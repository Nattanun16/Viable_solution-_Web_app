from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    faculty = models.CharField(max_length=200, blank=True)
    photo = models.ImageField(upload_to="profile_photos/", blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


# สร้าง profile อัตโนมัติเมื่อสร้าง User
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


class Problem(models.Model):
    CATEGORY_CHOICES = [
        ("WASTE", "ปริมาณขยะและเศษอาหาร"),
        ("POLLUTION", "มลพิษและการใช้พลังงาน"),
        ("WATER", "การจัดการน้ำ"),
        ("APP", "ระบบแอปพลิเคชันและการสื่อสาร"),
        ("COMMUNITY", "การมีส่วนร่วมของชุมชน (ประชาคมจุฬาฯ)"),
        ("OTHERS", "อื่นๆ"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "รอดำเนินการ"),
        ("PROGRESS", "กำลังดำเนินการแก้ไข"),
        ("COMPLETED", "แก้ไขเสร็จสิ้นแล้ว"),
    ]

    title = models.CharField(max_length=200)
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default="WASTE"
    )
    description = models.TextField(blank=True)
    location = models.CharField(max_length=300, blank=True)
    tags = models.CharField(max_length=300, blank=True)
    incident_date = models.DateField(null=True, blank=True)
    photo = models.ImageField(upload_to="problem_photos/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    reported_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_status_display()}] {self.title}"

    @property
    def tags_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]


class Suggestion(models.Model):
    problem = models.ForeignKey(
        Problem, on_delete=models.CASCADE, related_name="suggestions"
    )
    suggestion_text = models.TextField()
    votes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ข้อเสนอแนะสำหรับ: {self.problem.title[:30]}..."


class Comment(models.Model):
    problem = models.ForeignKey(
        Problem, on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    rating = models.IntegerField(default=0)  # 0-5 ดาว
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )
    is_reported = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.author.username}: {self.text[:30]}"
