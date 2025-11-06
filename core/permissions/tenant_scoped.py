from rest_framework.permissions import BasePermission, SAFE_METHODS

class TenantScopedPermission(BasePermission):
    """
    Autorise l'accès si l'auth HMAC a placé request.tenant.
    Tu peux enrichir par plan/quotas plus tard (app limits).
    """
    def has_permission(self, request, view):
        return bool(getattr(request, "tenant", None))
