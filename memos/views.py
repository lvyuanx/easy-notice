from datetime import date
from urllib.parse import urlencode

from django.contrib import messages
from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import MemoForm, MemoGroupForm
from .models import Memo, MemoGroup


def _redirect_back(request, fallback_name):
    next_url = request.POST.get("next", "").strip()
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect(fallback_name)


def _parse_iso_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _event_colors(memo):
    if memo.is_completed:
        return "#16a34a", "#15803d"
    if memo.priority == Memo.Priority.URGENT:
        return "#e11d48", "#be123c"
    if memo.priority == Memo.Priority.HIGH:
        return "#ea580c", "#c2410c"
    if memo.priority == Memo.Priority.MEDIUM:
        return "#0284c7", "#0369a1"
    return "#4f46e5", "#4338ca"


def memo_list(request):
    queryset = Memo.objects.select_related("group").all()
    groups = MemoGroup.objects.all()

    search = request.GET.get("q", "").strip()
    group_id = request.GET.get("group", "").strip()
    status = request.GET.get("status", "all").strip()
    priority = request.GET.get("priority", "").strip()
    sort = request.GET.get("sort", "default").strip()
    date_filter = request.GET.get("date", "").strip()

    if search:
        queryset = queryset.filter(Q(title__icontains=search) | Q(content__icontains=search))

    if group_id.isdigit():
        queryset = queryset.filter(group_id=int(group_id))

    if priority.isdigit():
        queryset = queryset.filter(priority=int(priority))

    if date_filter:
        try:
            due_date = date.fromisoformat(date_filter)
            queryset = queryset.filter(due_date=due_date)
        except ValueError:
            date_filter = ""

    local_today = timezone.localdate()

    if status == "active":
        queryset = queryset.filter(is_completed=False)
    elif status == "completed":
        queryset = queryset.filter(is_completed=True)
    elif status == "overdue":
        queryset = queryset.filter(is_completed=False, due_date__lt=local_today)

    if sort == "newest":
        queryset = queryset.order_by("-created_at")
    elif sort == "oldest":
        queryset = queryset.order_by("created_at")
    elif sort == "due":
        queryset = queryset.annotate(
            due_is_null=Case(
                When(due_date__isnull=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by("due_is_null", "due_date", "is_completed", "-is_pinned")
    elif sort == "priority":
        queryset = queryset.order_by("-priority", "is_completed", "-is_pinned", "due_date")

    stats = Memo.objects.aggregate(
        total=Count("id"),
        completed=Count("id", filter=Q(is_completed=True)),
        active=Count("id", filter=Q(is_completed=False)),
        overdue=Count("id", filter=Q(is_completed=False, due_date__lt=local_today)),
    )

    context = {
        "memos": queryset,
        "groups": groups,
        "search": search,
        "group_id": group_id,
        "status": status,
        "priority": priority,
        "sort": sort,
        "date_filter": date_filter,
        "priority_choices": Memo.Priority.choices,
        "stats": stats,
    }
    return render(request, "memos/memo_list.html", context)


def memo_calendar(request):
    today = timezone.localdate()
    selected_date = _parse_iso_date(request.GET.get("date")) or today

    undated_memos = (
        Memo.objects.select_related("group")
        .filter(due_date__isnull=True, is_completed=False)
        .order_by("-is_pinned", "-priority", "-updated_at")[:8]
    )

    context = {
        "initial_date": selected_date.isoformat(),
        "today": today,
        "undated_memos": undated_memos,
    }
    return render(request, "memos/calendar.html", context)


def memo_calendar_events_api(request):
    start_date = _parse_iso_date(request.GET.get("start"))
    end_date = _parse_iso_date(request.GET.get("end"))
    if not start_date or not end_date:
        return JsonResponse([], safe=False)

    memos = (
        Memo.objects.select_related("group")
        .filter(due_date__gte=start_date, due_date__lt=end_date)
        .order_by("due_date", "is_completed", "-is_pinned", "-priority")
    )

    events = []
    for memo in memos:
        background, border = _event_colors(memo)
        events.append(
            {
                "id": str(memo.id),
                "title": memo.title,
                "start": memo.due_date.isoformat(),
                "allDay": True,
                "backgroundColor": background,
                "borderColor": border,
                "textColor": "#ffffff",
                "extendedProps": {
                    "priority": memo.get_priority_display(),
                    "priority_value": memo.priority,
                    "is_completed": memo.is_completed,
                    "is_pinned": memo.is_pinned,
                    "group_name": memo.group.name if memo.group else "",
                    "group_color": memo.group.color if memo.group else "",
                    "content_preview": memo.content[:120],
                    "edit_url": reverse("memo_edit", args=[memo.id]),
                },
            }
        )

    return JsonResponse(events, safe=False)


def memo_calendar_day_api(request):
    target_date = _parse_iso_date(request.GET.get("date"))
    if not target_date:
        return JsonResponse(
            {
                "date": "",
                "date_label": "未选择日期",
                "count": 0,
                "list_url": reverse("memo_list"),
                "create_url": reverse("memo_create"),
                "memos": [],
            }
        )

    memos = (
        Memo.objects.select_related("group")
        .filter(due_date=target_date)
        .order_by("is_completed", "-is_pinned", "-priority", "-updated_at")
    )
    memo_list = []
    for memo in memos:
        memo_list.append(
            {
                "id": memo.id,
                "title": memo.title,
                "priority": memo.get_priority_display(),
                "priority_value": memo.priority,
                "is_completed": memo.is_completed,
                "is_pinned": memo.is_pinned,
                "group_name": memo.group.name if memo.group else "未分组",
                "group_color": memo.group.color if memo.group else "",
                "content_preview": memo.content[:120],
                "edit_url": reverse("memo_edit", args=[memo.id]),
            }
        )

    list_url = f"{reverse('memo_list')}?{urlencode({'date': target_date.isoformat(), 'sort': 'priority'})}"
    next_calendar_url = f"{reverse('memo_calendar')}?{urlencode({'date': target_date.isoformat()})}"
    create_url = f"{reverse('memo_create')}?{urlencode({'due_date': target_date.isoformat(), 'next': next_calendar_url})}"
    return JsonResponse(
        {
            "date": target_date.isoformat(),
            "date_label": target_date.strftime("%Y年%m月%d日"),
            "count": len(memo_list),
            "list_url": list_url,
            "create_url": create_url,
            "memos": memo_list,
        }
    )


def memo_create(request):
    next_url = request.GET.get("next", "").strip()
    due_date_default = _parse_iso_date(request.GET.get("due_date"))
    if request.method == "POST":
        form = MemoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "备忘录已创建。")
            return _redirect_back(request, "memo_list")
    else:
        initial = {"due_date": due_date_default} if due_date_default else None
        form = MemoForm(initial=initial)

    return render(
        request,
        "memos/memo_form.html",
        {"form": form, "is_create": True, "next_url": next_url},
    )


def memo_edit(request, pk):
    memo = get_object_or_404(Memo, pk=pk)
    next_url = request.GET.get("next", "").strip()
    if request.method == "POST":
        form = MemoForm(request.POST, instance=memo)
        if form.is_valid():
            form.save()
            messages.success(request, "备忘录已更新。")
            return _redirect_back(request, "memo_list")
    else:
        form = MemoForm(instance=memo)

    return render(
        request,
        "memos/memo_form.html",
        {"form": form, "memo": memo, "is_create": False, "next_url": next_url},
    )


@require_POST
def memo_delete(request, pk):
    memo = get_object_or_404(Memo, pk=pk)
    memo.delete()
    messages.success(request, "备忘录已删除。")
    return _redirect_back(request, "memo_list")


@require_POST
def memo_toggle_complete(request, pk):
    memo = get_object_or_404(Memo, pk=pk)
    memo.is_completed = not memo.is_completed
    memo.save(update_fields=["is_completed", "updated_at"])
    messages.success(request, "完成状态已更新。")
    return _redirect_back(request, "memo_list")


@require_POST
def memo_toggle_pin(request, pk):
    memo = get_object_or_404(Memo, pk=pk)
    memo.is_pinned = not memo.is_pinned
    memo.save(update_fields=["is_pinned", "updated_at"])
    messages.success(request, "置顶状态已更新。")
    return _redirect_back(request, "memo_list")


def group_list(request):
    if request.method == "POST":
        form = MemoGroupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "分组已创建。")
            return redirect("group_list")
    else:
        form = MemoGroupForm()

    groups = MemoGroup.objects.annotate(memo_count=Count("memos")).order_by("name")
    return render(request, "memos/group_list.html", {"form": form, "groups": groups})


def group_edit(request, pk):
    group = get_object_or_404(MemoGroup, pk=pk)
    if request.method == "POST":
        form = MemoGroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, "分组已更新。")
            return redirect("group_list")
    else:
        form = MemoGroupForm(instance=group)

    return render(request, "memos/group_form.html", {"form": form, "group": group})


@require_POST
def group_delete(request, pk):
    group = get_object_or_404(MemoGroup, pk=pk)
    group.delete()
    messages.success(request, "分组已删除。")
    return redirect("group_list")
