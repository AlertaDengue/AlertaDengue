from chunked_upload.views import ChunkedUploadCompleteView, ChunkedUploadView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import File
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from .forms import DBFForm
from .models import DBF, DBFChunkedUpload
from .tasks import import_dbf_to_database


class UploadSuccessful(LoginRequiredMixin, TemplateView):
    template_name = "upload_successful.html"

    def get_context_data(self, **kwargs):
        kwargs["last_uploaded"] = DBF.objects.filter(
            uploaded_by=self.request.user
        ).order_by("-uploaded_at")[:5]
        return super(UploadSuccessful, self).get_context_data(**kwargs)


class Upload(LoginRequiredMixin, FormView):
    form_class = DBFForm
    template_name = "dbf_upload.html"
    success_url = reverse_lazy("dbf:upload_successful")

    def post(self, request, *args, **kwargs):
        mutable_POST = self.request.POST.copy()
        mutable_POST["uploaded_by"] = request.user.id
        self.request.POST = mutable_POST
        return super(Upload, self).post(self.request, *args, **kwargs)

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
        return super(Upload, self).form_valid(form)

    def get_context_data(self, **kwargs):
        kwargs["last_uploaded"] = DBF.objects.filter(
            uploaded_by=self.request.user
        ).order_by("-uploaded_at")[:5]
        return super(Upload, self).get_context_data(**kwargs)


class DBFChunkedUploadView(ChunkedUploadView):

    model = DBFChunkedUpload
    field_name = "the_file"


class DBFChunkedUploadCompleteView(ChunkedUploadCompleteView):

    model = DBFChunkedUpload

    def get_response_data(self, chunked_upload, request):
        return {
            "filename": chunked_upload.filename,
            "chunked_upload_id": chunked_upload.id,
        }


# import os
# import time
# from django.contrib import messages
# from django.views.generic.edit import FormView
# from watchdog.observers import Observer
# from watchdog.events import FileSystemEventHandler
# from .models import DBF

# WATCH_DIRECTORY = "/path/to/watch/directory"  # Replace with the actual directory path


# class DBFEventHandler(FileSystemEventHandler):
#     def on_created(self, event):
#         if not event.is_directory:
#             file_path = event.src_path
#             file_name = os.path.basename(file_path)
#             dbf_id = os.path.splitext(file_name)[0]
#             if is_dbf_directory(dbf_id):
#                 dbf = DBF.objects.create(
#                     uploaded_by=None,
#                     file=file_path,
#                     export_date=metadata(today),
#                     notification_year=metadata(current_year),
#                     abbreviation="BR",
#                     municipio="None",
#                 )
#                 import_dbf_to_database.delay(dbf.id)
#                 success_message = (
#                     f"The file {dbf.file.name} was successfully sent for import."
#                 )
#                 messages.success(request, success_message)


# class UploadView(FormView):
#     template_name = "your_template.html"
#     success_url = "/success/url"

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.observer = Observer()

#     def start_watchdog(self):
#         event_handler = DBFEventHandler()
#         self.observer.schedule(event_handler, WATCH_DIRECTORY, recursive=False)
#         self.observer.start()

#     def stop_watchdog(self):
#         self.observer.stop()
#         self.observer.join()

#     def get(self, request, *args, **kwargs):
#         self.start_watchdog()
#         return super().get(request, *args, **kwargs)

#     def post(self, request, *args, **kwargs):
#         self.stop_watchdog()
#         return super().post(request, *args, **kwargs)

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         # Add any additional context data here, if needed
#         return context

#     def get_success_url(self):
#         return self.success_url

#     def dispatch(self, request, *args, **kwargs):
#         return super().dispatch(request, *args, **kwargs)

#     def get_form_kwargs(self):
#         kwargs = super().get_form_kwargs()
#         # Add any additional form kwargs here, if needed
#         return kwargs

#     def form_valid(self, form):
#         # Handle the form validation logic here, if needed
#         return super().form_valid(form)

#     def form_invalid(self, form):
#         # Handle the form invalidation logic here, if needed
#         return super().form_invalid(form)
