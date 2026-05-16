from django.db import models

class Problem(models.Model):
    # ตัวเลือกหมวดหมู่ปัญหา
    CATEGORY_CHOICES = [
        ('ROADS', 'ถนนและทางเท้า'),
        ('LIGHTS', 'ไฟฟ้าสาธารณะ'),
        ('WASTE', 'ขยะและสิ่งแวดล้อม'),
        ('SAFETY', 'ความปลอดภัย'),
        ('OTHERS', 'อื่นๆ'),
    ]
    
    # ตัวเลือกสถานะการดำเนินการ
    STATUS_CHOICES = [
        ('PENDING', 'รอดำเนินการ'),
        ('PROGRESS', 'กำลังดำเนินการแก้ไข'),
        ('COMPLETED', 'แก้ไขเสร็จสิ้นแล้ว'),
    ]

    title = models.CharField(max_length=200, verbose_name="หัวข้อปัญหา")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='ROADS', verbose_name="หมวดหมู่")
    description = models.TextField(verbose_name="รายละเอียดปัญหา")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="สถานะ")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="วันที่แจ้งเรื่อง")

    class Meta:
        verbose_name = "ปัญหาที่ร้องเรียน"
        verbose_name_plural = "ปัญหาที่ร้องเรียนทั้งหมด"

    def __str__(self):
        return f"[{self.get_status_display()}] {self.title}"


class Suggestion(models.Model):
    # ผูกกับตาราง Problem (ถ้าปัญหาถูกลบ ข้อเสนอแนะที่คู่กันจะโดนลบด้วย)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='suggestions', verbose_name="ปัญหาที่เกี่ยวข้อง")
    suggestion_text = models.TextField(verbose_name="ข้อเสนอแนะแนวทางแก้ไข")
    votes = models.IntegerField(default=0, verbose_name="คะแนนโหวตสนับสนุน")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="วันที่เสนอแนะ")

    class Meta:
        verbose_name = "ข้อเสนอแนะจากประชาชน"
        verbose_name_plural = "ข้อเสนอแนะทั้งหมด"

    def __str__(self):
        return f"ข้อเสนอแนะสำหรับ: {self.problem.title[:30]}..."