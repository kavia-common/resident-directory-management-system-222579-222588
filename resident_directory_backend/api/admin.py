from django.contrib import admin
from .models import Resident, Photo


class PhotoInline(admin.TabularInline):
    model = Photo
    extra = 0
    fields = ("image", "is_primary", "uploaded_at")
    readonly_fields = ("uploaded_at",)


@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = ("id", "first_name", "last_name", "apartment", "phone", "email", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("first_name", "last_name", "apartment", "phone", "email")
    inlines = [PhotoInline]


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ("id", "resident", "is_primary", "uploaded_at")
    list_filter = ("is_primary",)
    search_fields = ("resident__first_name", "resident__last_name", "resident__apartment")
