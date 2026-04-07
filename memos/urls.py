from django.urls import path

from . import views

urlpatterns = [
    path("", views.memo_list, name="memo_list"),
    path("calendar/", views.memo_calendar, name="memo_calendar"),
    path("calendar/api/events/", views.memo_calendar_events_api, name="memo_calendar_events_api"),
    path("calendar/api/day/", views.memo_calendar_day_api, name="memo_calendar_day_api"),
    path("memos/new/", views.memo_create, name="memo_create"),
    path("memos/<int:pk>/edit/", views.memo_edit, name="memo_edit"),
    path("memos/<int:pk>/delete/", views.memo_delete, name="memo_delete"),
    path("memos/<int:pk>/toggle-complete/", views.memo_toggle_complete, name="memo_toggle_complete"),
    path("memos/<int:pk>/toggle-pin/", views.memo_toggle_pin, name="memo_toggle_pin"),
    path("groups/", views.group_list, name="group_list"),
    path("groups/<int:pk>/edit/", views.group_edit, name="group_edit"),
    path("groups/<int:pk>/delete/", views.group_delete, name="group_delete"),
]
