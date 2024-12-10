from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import File
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import FormView
from chunked_upload.views import ChunkedUploadView, ChunkedUploadCompleteView

from . import models, forms


User = get_user_model()


class SINANUpload(LoginRequiredMixin, FormView):
    form_class = forms.SINANForm
    template_name = "sinan/index.html"
    success_url = reverse_lazy("upload:sinan_success")

    def post(self, request, *args, **kwargs):
        mutable_POST = self.request.POST.copy()
        mutable_POST["uploaded_by"] = request.user.id
        self.request.POST = mutable_POST
        return super().post(self.request, *args, **kwargs)

    def form_valid(self, form):
        chunked_upload = models.SINANChunkedUpload.objects.get(
            id=form.cleaned_data["upload_id"], user=self.request.user
        )
        uploaded_file = File(
            chunked_upload.file, form.cleaned_data["filename"]
        )
        print(uploaded_file)
        sinan_file = models.SINANUpload.objects.create(
            year=form.cleaned_data["notification_year"],
            uf=form.cleaned_data["abbreviation"],
            municipio=form.cleaned_data["municipio"] or None,
            file=uploaded_file,
            export_date=form.cleaned_data["export_date"],
            uploaded_by=self.request.user,
        )
        # import_dbf_to_database.delay(dbf.id)
        success_message = _(
            f"""
            O arquivo {sinan_file.file.name} exportado em 
            {sinan_file.export_date:%d/%m/%Y} com notificações do ano 
            {sinan_file.year} foi enviado com sucesso. Você será
            informado por email ({self.request.user.email}) assim que 
            o processo de importação for finalizado
            """
        )
        messages.success(self.request, success_message)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        kwargs["last_uploaded"] = models.SINANUpload.objects.filter(
            uploaded_by=self.request.user
        ).order_by("-uploaded_at")[:5]
        return super().get_context_data(**kwargs)


class SINANChunkedUploadView(ChunkedUploadView):
    model = models.SINANChunkedUpload


class SINANChunkedUploadCompleteView(ChunkedUploadCompleteView):
    model = models.SINANChunkedUpload

    def get_response_data(self, chunked_upload, request):
        return {
            "id": chunked_upload.id,
            "filename": chunked_upload.filename,
        }
