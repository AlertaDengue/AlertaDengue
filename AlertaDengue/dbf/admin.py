from django.contrib import admin
from .models import DBF

from dbf.models import SendToPartner


admin.site.register(DBF)


class SendToPartnerAdmin(admin.ModelAdmin):
    list_display = ['name', 'level', 'contact', 'mail', 'status']
    ordering = ['name']


admin.site.register(SendToPartner, SendToPartnerAdmin)
