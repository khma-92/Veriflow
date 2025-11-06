from django.contrib import admin
from .models import ApiKey

@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "key_id", "active", "is_expired", "last_used_at", "created_at", "name")
    list_filter = ("active", "tenant")
    search_fields = ("key_id", "tenant__name", "name")
    readonly_fields = ("created_at", "last_used_at")
