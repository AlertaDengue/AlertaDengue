from django.contrib import admin
from common.models import RequestPartnerData


class RequestPartnerDataAdmin(admin.ModelAdmin):
    list_display = ['name', 'level', 'contact', 'status']
    ordering = ['name']


admin.site.register(RequestPartnerData, RequestPartnerDataAdmin)
