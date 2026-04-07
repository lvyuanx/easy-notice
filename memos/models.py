from django.db import models
from django.utils import timezone


class MemoGroup(models.Model):
    name = models.CharField("分组名称", max_length=50, unique=True)
    description = models.CharField("分组说明", max_length=120, blank=True)
    color = models.CharField("分组颜色", max_length=7, default="#2563eb")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "备忘录分组"
        verbose_name_plural = "备忘录分组"

    def __str__(self):
        return self.name


class Memo(models.Model):
    class Priority(models.IntegerChoices):
        LOW = 1, "低"
        MEDIUM = 2, "中"
        HIGH = 3, "高"
        URGENT = 4, "紧急"

    title = models.CharField("标题", max_length=120)
    content = models.TextField("内容", blank=True)
    group = models.ForeignKey(
        MemoGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="memos",
        verbose_name="所属分组",
    )
    priority = models.PositiveSmallIntegerField(
        "优先级", choices=Priority.choices, default=Priority.MEDIUM
    )
    due_date = models.DateField("截止日期", null=True, blank=True)
    is_completed = models.BooleanField("已完成", default=False)
    is_pinned = models.BooleanField("置顶", default=False)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        ordering = ["is_completed", "-is_pinned", "due_date", "-updated_at"]
        verbose_name = "备忘录"
        verbose_name_plural = "备忘录"

    @property
    def is_overdue(self):
        if self.is_completed or not self.due_date:
            return False
        return self.due_date < timezone.localdate()

    def __str__(self):
        return self.title
