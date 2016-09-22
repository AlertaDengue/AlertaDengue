from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView
from dbf.models import DBF
from dbf.forms import DBFForm

class UploadSuccessful(LoginRequiredMixin, TemplateView):
    template_name = "upload_successful.html"


class Upload(LoginRequiredMixin, CreateView):
    model = DBF
    form_class = DBFForm
    template_name = "dbf_upload.html"
    success_url = reverse_lazy("dbf:upload_successful")

    def post(self, request, *args, **kwargs):
        self.request.POST['uploaded_by'] = request.user.id
        return super(Upload, self).post(self.request, *args, **kwargs)
