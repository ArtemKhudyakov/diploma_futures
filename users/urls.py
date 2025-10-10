from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LoginView
from django.urls import path, reverse_lazy
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .forms import CustomPasswordResetForm
from .views import (
    CustomLogoutView,
    UserCreateApiView,
    UserListAPIView,
    UserListHTMLView,
    UserListView,
    UserProfileRetrieveAPIView,
    UserProfileUpdateAPIView,
    UserProfileUpdateView,
    UserRegisterView,
    email_verification,
    toggle_user_block
)

app_name = "users"

urlpatterns = [
    path("login/", LoginView.as_view(template_name="users/login.html"), name="login"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
    path("register/", UserRegisterView.as_view(template_name="users/registration.html"), name="register"),
    path("profile/edit/", UserProfileUpdateView.as_view(), name="profile_edit"),
    path("email-confirm/<str:token>/", email_verification, name="email_verification"),
    path(
        "password_reset/",
        auth_views.PasswordResetView.as_view(
            form_class=CustomPasswordResetForm,
            template_name="users/password_reset.html",
            email_template_name="users/password_reset_email.html",
            subject_template_name="users/password_reset_subject.txt",
            success_url=reverse_lazy("users:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="users/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="users/password_reset_confirm.html",
            success_url=reverse_lazy("users:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="users/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
    path("manager/users/", UserListView.as_view(), name="user_list"),
    path("manager/users/toggle_block/<int:user_id>/", toggle_user_block, name="toggle_user_block"),
    path("api/users/", UserListAPIView.as_view(), name="api_user_list"),
    path("api/my-profile/", UserProfileRetrieveAPIView.as_view(), name="api_my_profile"),
    path("api/my-profile/update/", UserProfileUpdateAPIView.as_view(), name="api_my_profile_update"),
    path("api/profile/<int:pk>/", UserProfileRetrieveAPIView.as_view(), name="api_profile_detail"),
    path("api/profile/<int:pk>/update/", UserProfileUpdateAPIView.as_view(), name="api_profile_update_detail"),
    path("manager/users/html/", UserListHTMLView.as_view(), name="user_list_html"),
    path("api/login/", TokenObtainPairView.as_view(permission_classes=(AllowAny,)), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(permission_classes=(AllowAny,)), name="token_refresh"),
    path("api/register/", UserCreateApiView.as_view(), name="user_api_register"),
]
