from rest_framework import permissions


class CanEditUserProfile(permissions.BasePermission):
    """
    Разрешение для редактирования профиля:
    - Владелец может редактировать свой профиль
    - Менеджер может редактировать любой профиль
    - Админ может редактировать любой профиль
    """

    def has_object_permission(self, request, view, obj):
        """Настройка прав доступа для редактирования профиля"""
        # Владелец всегда может редактировать
        if obj == request.user:
            return True

        # Проверяем права менеджера/админа
        user_role = getattr(request.user, "role", None)
        is_manager = user_role == "manager"
        is_admin = request.user.is_staff

        return is_manager or is_admin


class CanViewUserList(permissions.BasePermission):
    """
    Разрешение для просмотра списка пользователей:
    - Только менеджеры и админы
    """

    def has_permission(self, request, view):
        """Настройка прав доступа для просмотра списка пользователей"""
        is_manager = request.user.role == "manager"
        is_admin = request.user.is_staff

        return is_manager or is_admin
