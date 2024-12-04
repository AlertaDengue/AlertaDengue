from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from chunked_upload.views import ChunkedUploadView, ChunkedUploadCompleteView

from .models import SINAN, Diseases, UFs
from .sinan.utils import EXPECTED_FIELDS, REQUIRED_FIELDS
from .tasks import sinan_split_by_uf_or_chunk
from . import models


User = get_user_model()


class SINANUploadSuccessful(LoginRequiredMixin, TemplateView):
    template_name = "sinan_success.html"

    def get_context_data(self, **kwargs):
        kwargs["last_uploaded"] = models.SINANUpload.objects.filter(
            uploaded_by=self.request.user
        ).order_by("-uploaded_at")[:5]
        return super().get_context_data(**kwargs)


class SINANUpload(LoginRequiredMixin, FormView):
    form_class = DBFForm
    template_name = "sinan.html"
    success_url = reverse_lazy("upload:sinan_success")

    def post(self, request, *args, **kwargs):
        mutable_POST = self.request.POST.copy()
        mutable_POST["uploaded_by"] = request.user.id
        self.request.POST = mutable_POST
        return super().post(self.request, *args, **kwargs)

    def form_valid(self, form):
        chunked_upload = DBFChunkedUpload.objects.get(
            id=form.cleaned_data["chunked_upload_id"], user=self.request.user
        )
        uploaded_file = File(
            chunked_upload.file, form.cleaned_data["filename"]
        )
        dbf = DBF.objects.create(
            uploaded_by=self.request.user,
            file=uploaded_file,
            export_date=form.cleaned_data["export_date"],
            notification_year=form.cleaned_data["notification_year"],
            abbreviation=form.cleaned_data["abbreviation"],
            municipio=form.cleaned_data["municipio"],
        )
        import_dbf_to_database.delay(dbf.id)
        success_message = _(
            f"""
            O arquivo {dbf.file.name} exportado em {dbf.export_date:%d/%m/%Y}
            com notificações do ano {dbf.notification_year}
            foi enviado com sucesso. Você será informado por email
            ({self.request.user.email}) assim que o processo de
            importação for finalizado,
            """
        )
        messages.success(self.request, success_message)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        kwargs["last_uploaded"] = DBF.objects.filter(
            uploaded_by=self.request.user
        ).order_by("-uploaded_at")[:5]
        return super().get_context_data(**kwargs)


class SINANChunkedUploadView(ChunkedUploadView):
    model = SINANChunkedUpload


class SINANChunkedUploadCompleteView(ChunkedUploadCompleteView):
    model = SINANChunkedUpload

    def get_response_data(self, chunked_upload, request):
        return {
            "filename": chunked_upload.filename,
            "chunked_upload_id": chunked_upload.id,
        }
