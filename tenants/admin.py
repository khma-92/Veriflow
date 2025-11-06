from django.contrib import admin
from .models import Tenant, Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "active", "per_minute", "per_day", "region", "created_at")
    list_filter = ("active", "region")
    search_fields = ("name", "slug")
    readonly_fields = ("created_at",)


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "plan", "status", "country_code", "support_email", "created_at", "updated_at")
    list_filter = ("status", "plan")
    search_fields = ("name", "support_email")
    readonly_fields = ("created_at", "updated_at", "last_usage_at")
