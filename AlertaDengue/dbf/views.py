from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.files.base import File
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from chunked_upload.views import ChunkedUploadView, ChunkedUploadCompleteView

from .models import DBF, DBFChunkedUpload
from .forms import DBFForm
from .tasks import import_dbf_to_database


class UploadSuccessful(LoginRequiredMixin, TemplateView):
    template_name = "upload_successful.html"

    def get_context_data(self, **kwargs):
        kwargs['last_uploaded'] = DBF.objects.filter(
            uploaded_by=self.request.user).order_by("-uploaded_at")[:5]
        return super(UploadSuccessful, self).get_context_data(**kwargs)


class Upload(LoginRequiredMixin, FormView):
    form_class = DBFForm
    template_name = "dbf_upload.html"
    success_url = reverse_lazy("dbf:upload_successful")

    def post(self, request, *args, **kwargs):
        mutable_POST = self.request.POST.copy()
        mutable_POST['uploaded_by'] = request.user.id
        self.request.POST = mutable_POST
        return super(Upload, self).post(self.request, *args, **kwargs)

    def form_valid(self, form):
        chunked_upload = DBFChunkedUpload.objects.get(
            id=form.cleaned_data['chunked_upload_id'],
            user=self.request.user
        )
        uploaded_file = File(chunked_upload.file, form.cleaned_data['filename'])
        dbf = DBF.objects.create(
            uploaded_by=self.request.user,
            file=uploaded_file,
            export_date=form.cleaned_data['export_date'],
            notification_year=form.cleaned_data['notification_year'],
            state_abbreviation=form.cleaned_data['state_abbreviation'],
            municipio=form.cleaned_data['municipio']
        )
        import_dbf_to_database.delay(dbf.id)
        success_message = _("O arquivo {} exportado em {:%d/%m/%Y} com notificações do ano {} "
                            "foi enviado com sucesso. Você será informado "
                            "por email ({}) assim que o processo de "
                            "importação for finalizado, ".format(
                                dbf.file.name, dbf.export_date,
                                dbf.notification_year, self.request.user.email))
        messages.success(self.request, success_message)
        return super(Upload, self).form_valid(form)


    def get_context_data(self, **kwargs):
        kwargs['last_uploaded'] = DBF.objects.filter(
            uploaded_by=self.request.user).order_by("-uploaded_at")[:5]
        return super(Upload, self).get_context_data(**kwargs)


class DBFChunkedUploadView(ChunkedUploadView):

    model = DBFChunkedUpload
    field_name = 'the_file'


class DBFChunkedUploadCompleteView(ChunkedUploadCompleteView):

    model = DBFChunkedUpload

    def get_response_data(self, chunked_upload, request):
        return {'filename': chunked_upload.filename, 'chunked_upload_id': chunked_upload.id}
