from django.contrib import admin
from .models import Problem, Suggestion, ProblemGroup, Comment, Vote, UserProfile

# เพิ่มเติม: ลงทะเบียนให้หน้าแอดมินมองเห็นและจัดการ "กลุ่มปัญหาที่รวมเข้าด้วยกัน" ได้ด้วย
@admin.register(ProblemGroup)
class ProblemGroupAdmin(admin.ModelAdmin):
    list_display = ("main_title", "category", "status", "created_at")
    list_filter = ("category", "status", "created_at")
    search_fields = ("main_title", "category")
    list_editable = ("status",)

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    # ปรับปรุง: เพิ่มคอลัมน์ "group" (กลุ่มปัญหาซ้ำ) และเปลี่ยนชื่อฟิลด์วันเวลาเล็กน้อยให้ตรงตามโมเดล
    list_display = ("title", "group", "category", "status", "created_at")
    list_filter = ("category", "status", "created_at")
    search_fields = ("title", "description")
    list_editable = ("status",)

@admin.register(Suggestion)
class SuggestionAdmin(admin.ModelAdmin):
    # ปรับปรุง: เปลี่ยน problem -> group และเปลี่ยน suggestion_text -> description
    list_display = ("group", "suggested_by", "created_at")
    search_fields = ("description",)

# ลงทะเบียนตารางคอมเมนต์และตารางโหวตเสริมเข้าไป เพื่อให้แอดมินเข้าไปคัดกรองหรือตรวจสอบย้อนหลังได้
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("suggestion", "user", "stance", "is_approved", "created_at")
    list_filter = ("stance", "is_approved", "created_at")
    list_editable = ("is_approved",) # แอดมินสามารถกดติ๊กถูกเพื่ออนุมัติคอมเมนต์ผ่านหน้าตารางได้เลย

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("user", "vote_type", "problem", "suggestion", "comment", "created_at")
    list_filter = ("vote_type", "created_at")
    
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "student_id", "faculty")
    search_fields = ("student_id", "user__username")
    list_filter = ("faculty",)    