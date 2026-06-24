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
    list_editable = ("status", "is_approved")
    actions = ["approve_problems"]

    @admin.action(description="✅ อนุมัติปัญหาที่เลือก")
    def approve_problems(self, request, queryset):
        queryset.update(is_approved=True)


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
