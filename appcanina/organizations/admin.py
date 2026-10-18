from django.contrib import admin
from .models import Organization, OrganizationMembership


class OrganizationMembershipInline(admin.TabularInline):
    model = OrganizationMembership
    extra = 0


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "locality", "is_verified", "donation_alias", "is_business_profile")
    list_filter = ("kind", "is_verified", "is_business_profile")
    search_fields = ("name", "donation_alias")
    inlines = [OrganizationMembershipInline]
