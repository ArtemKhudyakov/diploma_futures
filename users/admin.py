from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


class UserAdmin(BaseUserAdmin):
    list_display = ("id", "username", "email", "role", "is_blocked", "is_staff", "is_superuser")
    list_filter = ("role", "is_blocked", "is_staff", "is_superuser")
    search_fields = ("username", "email")
    ordering = ("username",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("email", "country", "phone", "avatar")}),
        (_("Telegram settings"), {"fields": ("telegram_chat_id", "telegram_username", "telegram_notifications")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_blocked",
                    "is_verified",
                    "is_staff",
                    "is_superuser",
                    "role",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2", "role"),
            },
        ),
    )

    actions = ["block_users", "unblock_users", "make_managers", "make_regular_users"]

    def block_users(self, request, queryset):
        queryset.update(is_blocked=True)
        self.message_user(request, "Выбранные пользователи заблокированы")

    block_users.short_description = "Заблокировать пользователей"

    def unblock_users(self, request, queryset):
        queryset.update(is_blocked=False)
        self.message_user(request, "Выбранные пользователи разблокированы")

    unblock_users.short_description = "Разблокировать пользователей"

    def make_managers(self, request, queryset):
        queryset.update(role="manager")
        self.message_user(request, "Выбранные пользователи стали менеджерами")

    make_managers.short_description = "Сделать менеджерами"

    def make_regular_users(self, request, queryset):
        queryset.update(role="users")
        self.message_user(request, "Выбранные пользователи стали обычными пользователями")

    make_regular_users.short_description = "Сделать обычными пользователями"


admin.site.register(User, UserAdmin)

