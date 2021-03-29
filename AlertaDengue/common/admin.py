from django.contrib import admin
from common.models import SendToPartner


class SendToPartnerAdmin(admin.ModelAdmin):
    list_display = ['name', 'level', 'contact', 'status']
    ordering = ['name']

    def save_model(self, request, obj, change):
        obj.SendToPartner.save()
        obj.save()


admin.site.register(SendToPartner, SendToPartnerAdmin)
