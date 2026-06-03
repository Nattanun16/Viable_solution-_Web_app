from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# ==========================================
# 1. ข้อมูลผู้ใช้งานจุฬาฯ 
# ==========================================
class UserProfile(models.Model):
    # 1. กำหนดรายการตัวเลือกคณะทั้งหมดในจุฬาฯ ไว้เป็นลิสต์ 
    FACULTY_CHOICES = [
        ("EDUCATION", "คณะครุศาสตร์"),
        ("PSYCHOLOGY", "คณะจิตวิทยา"),
        ("DENTISTRY", "คณะทันตแพทยศาสตร์"),
        ("LAW", "คณะนิติศาสตร์"),
        ("COMMUNICATION_ARTS", "คณะนิเทศศาสตร์"),
        ("NURSING", "คณะพยาบาลศาสตร์"),
        ("COMMERCE_ACCOUNTANCY", "คณะพาณิชยศาสตร์และการบัญชี"),
        ("POLITICAL_SCIENCE", "คณะรัฐศาสตร์"),
        ("SCIENCE", "คณะวิทยาศาสตร์"),
        ("SPORTS_SCIENCE", "คณะวิทยาศาสตร์การกีฬา"),
        ("ENGINEERING", "คณะวิศวกรรมศาสตร์"),
        ("FINE_APPLIED_ARTS", "คณะศิลปกรรมศาสตร์"),
        ("ARCHITECTURE", "คณะสถาปัตยกรรมศาสตร์"),
        ("ALLIED_HEALTH_SCIENCES", "คณะสหเวชศาสตร์"),
        ("VETERINARY_SCIENCE", "คณะสัตวแพทยศาสตร์"),
        ("ARTS", "คณะอักษรศาสตร์"),
        ("INTEGRATED_AGRICULTURE", "คณะเกษตรศาสตร์บูรณาการ"),
        ("PHARMACEUTICAL_SCIENCES", "คณะเภสัชศาสตร์"),
        ("ECONOMICS", "คณะเศรษฐศาสตร์"),
        ("MEDICINE", "คณะแพทยศาสตร์"),
        ("OTHERS", "บุคลากร / หน่วยงานอื่น ๆ"),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    first_name = models.CharField(max_length=100, blank=True)   # เพิ่ม: ชื่อจริง
    last_name = models.CharField(max_length=100, blank=True)    # เพิ่ม: นามสกุล
    student_id = models.CharField(max_length=10, blank=True, unique=True, null=True) # เพิ่ม: รหัสนิสิต 10 หลัก
    faculty = models.CharField(max_length=200, blank=True)     # โค้ดเดิม
    photo = models.ImageField(upload_to="profile_photos/", blank=True, null=True) # โค้ดเดิม

    # 2. ⚡ จุดที่ต้องแก้: เพิ่มตัวแปร choices และกำหนดค่าเริ่มต้นดักไว้
    faculty = models.CharField(
        max_length=200, 
        choices=FACULTY_CHOICES,  # สั่งผูกเข้ากับลิสต์รายการคณะด้านบน 🎯
        default="SCIENCE"         # ค่าเริ่มต้นถ้าไม่ได้เลือก ให้เป็นคณะวิทยาศาสตร์ไว้ก่อน
    )
    photo = models.ImageField(upload_to="profile_photos/", blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

# สร้าง profile อัตโนมัติเมื่อสร้าง User (โค้ดเดิม)
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


# ==========================================
# 2. เพิ่มเติม: กลุ่มมัดรวมปัญหาที่ซ้ำกัน (Problem Groups)
# ==========================================
# รองรับความต้องการของพี่: ปัญหาเหมือนกันจะถูก AI หรือแอดมินจัดให้อยู่กลุ่มเดียวกัน
class ProblemGroup(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "รอดำเนินการ"),
        ("PROGRESS", "กำลังดำเนินการแก้ไข"),
        ("COMPLETED", "แก้ไขเสร็จสิ้นแล้ว"),
    ]
    main_title = models.CharField(max_length=200) # หัวข้อหลักสั้นๆ ที่ AI/คน สรุปให้
    category = models.CharField(max_length=50)   # หมวดหมู่ประเภท
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.status}] Group: {self.main_title}"


# ==========================================
# 3. ตารางปัญหาร้องเรียน (โค้ดเดิม + เพิ่มการผูกกลุ่มปัญหาและสื่อ)
# ==========================================
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

    # เพิ่ม: ผูกกับกลุ่มปัญหาที่เหมือนกัน (ถ้าเป็นโพสต์แรกของปัญหานั้น หรือยังไม่ซ้ำจะเป็น null)
    group = models.ForeignKey(ProblemGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name="contained_problems")
    
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="WASTE")
    description = models.TextField(blank=True)
    location = models.CharField(max_length=300, blank=True)
    tags = models.CharField(max_length=300, blank=True)
    incident_date = models.DateField(null=True, blank=True) # วันเวลาที่พบนิสิตระบุ
    
    photo = models.ImageField(upload_to="problem_photos/", blank=True, null=True) # รองรับรูปภาพ
    media_file = models.FileField(upload_to="problem_files/", blank=True, null=True) # เพิ่ม: รองรับไฟล์อื่นๆ หรือ วิดีโอ (ไม่บังคับ)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_status_display()}] {self.title}"


# ==========================================
# 4. หน้าคอมเมนต์วิธีแก้ (ปรับจากโค้ดเดิมให้ผูกกับกลุ่มปัญหาที่มัดรวมไว้)
# ==========================================
class Suggestion(models.Model):
    # ปรับ: ให้เสนอวิธีแก้เข้าสู่ "กลุ่มปัญหาที่รวมไว้" แทนปัญหาเดี่ยวๆ
    group = models.ForeignKey(ProblemGroup, on_delete=models.CASCADE, related_name="suggestions", null=True)
    suggested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True) # คนเสนอวิธีแก้
    suggestion_text = models.TextField()
    media_file = models.FileField(upload_to="suggestion_media/", blank=True, null=True) # เพิ่ม: แนบไฟล์ รูปภาพ วิดีโอ ได้ตามบรีฟใหม่
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ข้อเสนอแนะสำหรับกลุ่มปัญหา: {self.group.main_title[:30]}..."


# ==========================================
# 5. เพิ่มเติม: ตารางคอมเมนต์เสริมต่อวิธีแก้ไข (แยกฝั่งเห็นด้วย/ไม่เห็นด้วย)
# ==========================================
class Comment(models.Model):
    STANCE_CHOICES = [
        ('AGREE', 'เห็นด้วย'),
        ('DISAGREE', 'ไม่เห็นด้วย'),
    ]
    suggestion = models.ForeignKey(Suggestion, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    comment_text = models.TextField()
    media_file = models.FileField(upload_to="comment_media/", blank=True, null=True) # ไฟล์ รูปภาพ วิดีโอ ประกอบ
    stance = models.CharField(max_length=10, choices=STANCE_CHOICES) # บังคับแยกฝั่ง
    is_approved = models.BooleanField(default=False) # แอดมินตรวจสอบคัดกรองก่อนแสดงผล
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment ({self.stance}) by {self.user.username}"


# ==========================================
# 6. เพิ่มเติม: ระบบโหวต ไลค์ / ดิสไลค์ (Votes Tracker)
# ==========================================
# ใช้จัดการระบบกด Like / Dislike ของทั้งปัญหา วิธีแก้ และคอมเมนต์ เพื่อกันนิสิตปั้มโหวตซ้ำ
class Vote(models.Model):
    VOTE_CHOICES = [
        ('LIKE', 'เห็นด้วย / ไลค์'),
        ('DISLIKE', 'ไม่เห็นด้วย / ดิสไลค์'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # จะโหวตให้สิ่งไหน สิ่งนั้นจะมีค่า โครงสร้างที่เหลือจะเป็นโมเดลว่าง (Null)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, null=True, blank=True, related_name="votes")
    suggestion = models.ForeignKey(Suggestion, on_delete=models.CASCADE, null=True, blank=True, related_name="votes")
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True, related_name="votes")
    
    vote_type = models.CharField(max_length=10, choices=VOTE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # ข้อกำหนดระบบ: 1 คน กดโหวตไอเทมชิ้นเดิมซ้ำได้แค่ครั้งเดียว
        constraints = [
            models.UniqueConstraint(fields=['user', 'problem'], name='unique_user_problem_vote'),
            models.UniqueConstraint(fields=['user', 'suggestion'], name='unique_user_suggestion_vote'),
            models.UniqueConstraint(fields=['user', 'comment'], name='unique_user_comment_vote'),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.vote_type}"