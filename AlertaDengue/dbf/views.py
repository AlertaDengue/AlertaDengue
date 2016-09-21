from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView
from dbf.models import DBF

class UploadSuccessful(LoginRequiredMixin, TemplateView):
    template_name = "upload_successful.html"

class Upload(LoginRequiredMixin, CreateView):
    model = DBF
    fields = ["file", "export_date", "notification_year"]
    template_name = "dbf_upload.html"
    success_url = reverse_lazy("dbf:upload_successful")
