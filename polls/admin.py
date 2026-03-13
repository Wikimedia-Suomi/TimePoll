from django.contrib import admin

from .models import Identity, Poll, PollOption, PollVote


@admin.register(Identity)
class IdentityAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)


class PollOptionInline(admin.TabularInline):
    model = PollOption
    extra = 0


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "identifier",
        "title",
        "creator",
        "window_starts_at",
        "window_ends_at",
        "slot_minutes",
        "daily_start_hour",
        "daily_end_hour",
        "allowed_weekdays",
        "timezone_name",
        "is_closed",
        "created_at",
        "closed_at",
    )
    list_filter = ("is_closed",)
    search_fields = ("title", "identifier", "creator__name")
    inlines = [PollOptionInline]


@admin.register(PollVote)
class PollVoteAdmin(admin.ModelAdmin):
    list_display = ("id", "poll_option", "voter", "status", "updated_at")
    list_filter = ("status",)
    search_fields = ("voter__name",)
