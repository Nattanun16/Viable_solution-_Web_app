from django.contrib import admin
from .models import Problem, Suggestion

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    # เลือกคอลัมน์ที่จะโชว์ในหน้าตารางแอดมิน
    list_display = ('title', 'category', 'status', 'created_at')
    # เพิ่มแถบตัวกรองข้อมูลด้านขวา
    list_filter = ('category', 'status', 'created_at')
    # เพิ่มช่องค้นหาข้อมูล
    search_fields = ('title', 'description')
    # ยอมให้กดเปลี่ยนสถานะปัญหาในหน้าตารางได้เลย
    list_editable = ('status',)

@admin.register(Suggestion)
class SuggestionAdmin(admin.ModelAdmin):
    list_display = ('problem', 'votes', 'created_at')
    search_fields = ('suggestion_text',)