from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import File
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import FormView, View
from django.shortcuts import render
from chunked_upload.views import ChunkedUploadView, ChunkedUploadCompleteView

from . import models, forms

from loguru import logger

User = get_user_model()


class SINANDashboard(LoginRequiredMixin, View):
    template_name = "sinan/index.html"

    def get(self, request, *args, **kwargs):
        context = {}
        return render(request, self.template_name, context)


class SINANUpload(LoginRequiredMixin, FormView):
    form_class = forms.SINANForm
    template_name = "sinan/card.html"
    success_url = reverse_lazy("upload:sinan")

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
        sinan_file = models.SINANUpload.objects.create(
            uploaded_by=self.request.user,
            cid10=form.cleaned_data["cid10"],
            uf=form.cleaned_data["uf"],
            year=form.cleaned_data["notification_year"],
            file=uploaded_file,
        )
        # import_dbf_to_database.delay(dbf.id)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filename = self.request.GET.get("filename", "")
        context["filename"] = filename
        return context


class SINANChunkedUploadView(ChunkedUploadView):
    model = models.SINANChunkedUpload

    def delete(self, request, *args, **kwargs):
        upload_id = kwargs.get('upload_id')
        try:
            upload = self.model.objects.get(upload_id=upload_id)
            if upload.user != request.user:
                raise PermissionDenied("Forbidden")
            upload.file.delete()
            upload.delete()
            return JsonResponse(
                {"success": True, "message": f"{upload.file.name}"},
                status=200
            )
        except self.model.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Unknown upload"},
                status=404
            )


class SINANChunkedUploadCompleteView(ChunkedUploadCompleteView):
    model = models.SINANChunkedUpload

    def get_response_data(self, chunked_upload, request):
        logger.info(f"Chunked Upload Data: {chunked_upload.__dict__}")
        return {
            "id": chunked_upload.id,
            "filename": chunked_upload.filename,
        }
