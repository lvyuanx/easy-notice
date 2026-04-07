from django.contrib import admin

from .models import Memo, MemoGroup


@admin.register(MemoGroup)
class MemoGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "color", "created_at")
    search_fields = ("name", "description")


@admin.register(Memo)
class MemoAdmin(admin.ModelAdmin):
    list_display = ("title", "group", "priority", "due_date", "is_pinned", "is_completed", "updated_at")
    list_filter = ("priority", "is_completed", "is_pinned", "group")
    search_fields = ("title", "content")
