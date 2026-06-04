from django.contrib import admin
from .models import Problem, Suggestion, Comment


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "reported_by", "created_at")
    list_filter = ("category", "status", "created_at")
    search_fields = ("title", "description")
    list_editable = ("status",)


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
