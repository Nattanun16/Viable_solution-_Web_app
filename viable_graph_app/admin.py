from django.contrib import admin
from .models import Problem, Suggestion, Comment


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "status",
        "is_approved",
        "reported_by",
        "created_at",
    )
    list_filter = ("category", "status", "is_approved", "created_at")
    search_fields = ("title", "description")
    list_editable = (
        "status",
        "is_approved",
    ) 
    actions = ["approve_problems", "reject_problems"]

    def approve_problems(self, request, queryset):
        queryset.update(is_approved=True)
    approve_problems.short_description = "✅ อนุมัติปัญหาที่เลือก"

    def reject_problems(self, request, queryset):
        queryset.update(is_approved=False)
    reject_problems.short_description = "❌ ไม่อนุมัติปัญหาที่เลือก"


@admin.register(Suggestion)
class SuggestionAdmin(admin.ModelAdmin):
    list_display = ("problem", "votes", "created_at")
    search_fields = ("suggestion_text",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("author", "problem", "text", "rating", "is_reported", "created_at")
    list_filter = ("is_reported", "rating", "created_at")
    search_fields = ("text", "author__username")
    list_editable = ("is_reported",)
