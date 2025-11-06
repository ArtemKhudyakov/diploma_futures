from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField

from config import settings


class User(AbstractUser):
    username = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Имя пользователя",
        help_text="Введите имя пользователя",
    )
    email = models.EmailField(
        unique=True,
        blank=False,
        null=False,
        verbose_name="email",
        help_text="Введите адрес электронной почты",
    )
    country = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Страна",
        help_text="Введите страну",
    )

    city = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Город",
        help_text="Введите город",
    )

    phone = PhoneNumberField(
        blank=True,
        null=True,
        verbose_name="Телефон",
        help_text="Введите номер телефона",
    )

    avatar = models.ImageField(
        upload_to="users/avatars",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=["jfif", "jpg", "jpeg", "png"])],
        verbose_name="Аватар",
        help_text="Загрузите изображение аватара",
    )
    token = models.CharField(max_length=100, verbose_name="Токен", blank=True, null=True)
    is_verified = models.BooleanField(default=False, verbose_name="Подтвержден")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = [
        "username",
    ]

    telegram_chat_id = models.BigIntegerField(
        blank=True,
        null=True,
        unique=True,
        verbose_name="ID чата в Telegram",
        help_text="Уникальный идентификатор чата для Telegram уведомлений",
    )
    telegram_username = models.CharField(max_length=100, blank=True, null=True, verbose_name="Username в Telegram")
    telegram_notifications = models.BooleanField(
        default=True, verbose_name="Telegram уведомления", help_text="Включены ли уведомления в Telegram"
    )

    ROLES = (("users", "Пользователь"), ("manager", "Менеджер"))
    role = models.CharField(max_length=10, choices=ROLES, default="users", verbose_name="Роль")
    is_blocked = models.BooleanField(default=False, verbose_name="Заблокирован")

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        db_table = "users"
        permissions = [
            ("block_user", "Может блокировать пользователей"),
            ("disable_mailing", "Может отключать рассылки"),
        ]


class TelegramUser(models.Model):
    """Модель для хранения Telegram пользователей"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="telegram", verbose_name="Пользователь"
    )
    chat_id = models.BigIntegerField(
        unique=True, verbose_name="ID чата в Telegram", help_text="Уникальный идентификатор чата с пользователем"
    )
    username = models.CharField(max_length=100, blank=True, null=True, verbose_name="Username в Telegram")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата подключения")

    class Meta:
        verbose_name = "Telegram пользователь"
        verbose_name_plural = "Telegram пользователи"

    def __str__(self):
        return f"{self.user.username} ({self.chat_id})"


from django.db import models

# Create your models here.
