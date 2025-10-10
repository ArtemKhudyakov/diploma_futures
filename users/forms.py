from django import forms
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.template import loader

from .models import User


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise ValidationError("Пользователь с таким email уже существует.")
        return email

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise ValidationError("Пользователь с таким именем уже существует")
        return username

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "country",
            "phone",
            "avatar",
            "password1",
            "password2",
        )


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "email", "country", "phone", "avatar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].disabled = True  # Имя пользователя нельзя менять
        self.fields["email"].disabled = True  # Email тоже нельзя менять


class CustomPasswordResetForm(PasswordResetForm):
    def send_mail(
        self, subject_template_name, email_template_name, context, from_email, to_email, html_email_template_name=None
    ):
        """
        Кастомная отправка письма для сброса пароля
        """
        subject = loader.render_to_string(subject_template_name, context)
        # Убираем переносы строк в subject
        subject = "".join(subject.splitlines())
        body = loader.render_to_string(email_template_name, context)

        send_mail(
            subject=subject,
            message=body,
            from_email=settings.EMAIL_HOST_USER,  # Используем email из настроек
            recipient_list=[to_email],
            fail_silently=False,
        )
