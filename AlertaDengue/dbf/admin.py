from dbf.models import SendToPartner
from django.contrib import admin

from .models import DBF

admin.site.register(DBF)


class SendToPartnerAdmin(admin.ModelAdmin):
    list_display = ["name", "level", "contact", "email", "status"]
    ordering = ["name"]


admin.site.register(SendToPartner, SendToPartnerAdmin)
