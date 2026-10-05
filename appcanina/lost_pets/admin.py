from django.contrib import admin

from .models import LostPetReport, Sighting


class SightingInline(admin.TabularInline):
    model = Sighting
    extra = 0
    readonly_fields = ("reporter", "created_at")


@admin.register(LostPetReport)
class LostPetReportAdmin(admin.ModelAdmin):
    list_display = ("name", "species", "area_label", "last_seen_at", "status", "reporter")
    list_filter = ("status", "species")
    search_fields = ("name", "breed", "area_label")
    inlines = [SightingInline]


@admin.register(Sighting)
class SightingAdmin(admin.ModelAdmin):
    list_display = ("report", "seen_at", "area_label", "status", "reporter")
    list_filter = ("status",)
    search_fields = ("report__name", "area_label")
