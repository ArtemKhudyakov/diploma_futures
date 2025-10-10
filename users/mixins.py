from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied

# class ManagerRequiredMixin:
#     """Только для менеджеров (role='manager')"""
#
#     def dispatch(self, request, *args, **kwargs):
#         if not request.users.is_authenticated or request.users.role != "manager":
#             raise PermissionDenied("Доступ только для менеджеров")
#         return super().dispatch(request, *args, **kwargs)


class UserAccessMixin:
    """Пользователь может работать только со своими объектами"""

    def get_object(self, queryset=None):
        # Явно получаем объект
        obj = super().get_object(queryset) if queryset else super().get_object()
        return obj

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not request.user.is_authenticated or (obj.owner != request.user and request.user.role != "manager"):
            raise PermissionDenied("Нет доступа к этому объекту")
        return super().dispatch(request, *args, **kwargs)


class ManagerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Миксин только для менеджеров и админов"""

    def test_func(self):
        return self.request.user.role == "manager" or self.request.user.is_staff
