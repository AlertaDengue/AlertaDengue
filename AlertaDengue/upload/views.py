from pathlib import Path

import humanize
import json

from psycopg2.extras import DictCursor

from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import JsonResponse, QueryDict, HttpResponseNotFound
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import File
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import FormView, View
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import render, redirect
from chunked_upload.views import ChunkedUploadView, ChunkedUploadCompleteView

from . import models, forms
from ad_main.settings import get_sqla_conn

User = get_user_model()
Engine = get_sqla_conn(database="dengue")


class SINANDashboard(LoginRequiredMixin, View):
    template_name = "sinan/index.html"

    @never_cache
    def get(self, request, *args, **kwargs):
        context = {}
        return render(request, self.template_name, context)


class SINANOverview(LoginRequiredMixin, View):
    template_name = "sinan/overview.html"

    @never_cache
    def get(self, request, *args, **kwargs):
        sinan_upload_id = kwargs.get('sinan_upload_id')
        context = {}

        try:
            sinan = models.SINANUpload.objects.get(
                pk=sinan_upload_id,
                upload__user=request.user
            )
        except models.SINANUpload.DoesNotExist:
            messages.error(request, "Upload not found")
            return redirect("upload:sinan")

        context["sinan_upload_id"] = sinan_upload_id
        context["filename"] = sinan.upload.filename
        context["size"] = humanize.naturalsize(sinan.upload.file.size)
        context["inserts"] = sinan.status.inserts
        context["updates"] = sinan.status.updates
        context["uploaded_at"] = sinan.uploaded_at
        context["time_spend"] = f"{sinan.status.time_spend:.2f}"
        context["logs"] = sinan.status.read_logs("INFO")
        return render(request, self.template_name, context)


class SINANStatus(LoginRequiredMixin, View):
    template_name = "sinan/status.html"

    @never_cache
    def get(self, request, *args, **kwargs):
        sinan_upload_id = kwargs.get('sinan_upload_id')
        context = {}

        try:
            sinan = models.SINANUpload.objects.get(
                pk=sinan_upload_id,
                upload__user=request.user
            )
        except models.SINANUpload.DoesNotExist:
            return JsonResponse({"error": "Upload not found"}, safe=True)

        context["id"] = sinan.pk
        context["filename"] = sinan.upload.filename
        context["status"] = sinan.status.status
        context["uploaded_at"] = sinan.uploaded_at

        if sinan.status.status == 1:
            context["inserts"] = self.humanizer(sinan.status.inserts)
            context["updates"] = self.humanizer(sinan.status.updates)

            hours, remainder = divmod(sinan.status.time_spend, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours > 0:
                time_spend = f"{int(hours)}:{int(minutes)}:{int(seconds)}"
            elif minutes > 0:
                time_spend = f"{int(minutes)}:{int(seconds)}"
            else:
                time_spend = f"{int(seconds)}s"

            context["time_spend"] = time_spend

        if sinan.status.status == 2:
            error_message = (
                sinan.status.read_logs(level="ERROR")[0].split(" - ")[1]
            )
            context["error"] = error_message

        return render(request, self.template_name, context)

    def humanizer(self, integer) -> str:
        word = humanize.intword(integer)

        suffixes = {
            "thousand": "k",
            "million": "M",
            "billion": "B"
        }

        for suffix in suffixes:
            if suffix in word:
                word = word.replace(f" {suffix}", suffixes[suffix])

        return word


class SINANUpload(LoginRequiredMixin, FormView):
    form_class = forms.SINANForm
    template_name = "sinan/card.html"
    success_url = reverse_lazy("upload:sinan")

    def post(self, request, *args, **kwargs):
        post = request.POST.copy()
        post["uploaded_by"] = request.user.id
        self.request.POST = post
        return super().post(self.request, *args, **kwargs)

    def form_valid(self, form):
        upload = models.SINANChunkedUpload.objects.get(
            upload_id=form.cleaned_data["upload_id"], user=self.request.user
        )
        sinan_file = models.SINANUpload.objects.create(
            cid10=form.cleaned_data["cid10"],
            uf=form.cleaned_data["uf"],
            year=form.cleaned_data["notification_year"],
            upload=upload,
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        disease = {
            "DENG": "A90",
            "CHIK": "A92.0",
            "ZIKA": "A928",
        }

        context = super().get_context_data(**kwargs)

        if self.request.method == "POST":
            return context

        filename = self.request.GET.get("filename", "")

        for uf in models.UF_CODES:
            if uf in str(Path(filename).with_suffix("")).upper():
                context["form"] = self.get_form(self.get_form_class())
                context["form"].fields["uf"].initial = uf

        for dis in disease:
            if dis in str(Path(filename).with_suffix("")).upper():
                context["form"] = self.get_form(self.get_form_class())
                context["form"].fields["cid10"].initial = disease[dis]

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
        return {
            "id": chunked_upload.id,
            "filename": chunked_upload.filename,
        }


@never_cache
@csrf_protect
def get_user_uploads(request):
    context = {}
    if request.user.is_superuser:
        uploads = models.SINANUpload.objects.all()
    elif request.user.is_staff:
        uploads = models.SINANUpload.objects.filter(upload__user=request.user)
    else:
        uploads = models.SINANUpload.objects.none()
    context["uploads"] = list(
        uploads.order_by("-uploaded_at").values_list("id", flat=True)
    )
    return JsonResponse(context)


@never_cache
@csrf_protect
def overview_charts_limit_offset(request):
    offset = request.GET.get("offset")
    limit = request.GET.get("limit")
    id_type = request.GET.get("id_type")

    if offset is None or limit is None or not id_type:
        return JsonResponse(
            {"error": "missing 'offset', 'limit' or 'id_type' parameters"},
            status=400
        )

    limit, offset = int(limit), int(offset)

    try:
        sinan = models.SINANUpload.objects.get(
            pk=request.GET.get("sinan_upload_id")
        )
    except models.SINANUpload.DoesNotExist:
        return HttpResponseNotFound(
            json.dumps({"error": "Upload not found"}),
            content_type="application/json"
        )

    queries = {
        "epiweek": (
            'SELECT se_notif, ano_notif, COUNT(*) AS count '
            'FROM "Municipio"."Notificacao" '
            'WHERE id IN ({}) GROUP BY se_notif, ano_notif;'
        ),
        "cs_sexo": (
            'SELECT cs_sexo, COUNT(*) AS count '
            'FROM "Municipio"."Notificacao" '
            'WHERE id IN ({}) GROUP BY cs_sexo;'
        ),
        "criterio": (
            'SELECT criterio, COUNT(*) AS count '
            'FROM "Municipio"."Notificacao" '
            'WHERE id IN ({}) GROUP BY criterio;'
        ),
        "municipio_geocodigo": (
            'SELECT municipio_geocodigo, COUNT(*) AS count '
            'FROM "Municipio"."Notificacao" '
            'WHERE id IN ({}) GROUP BY municipio_geocodigo;'
        )
    }
    results = {}
    ids = sinan.status.list_ids(offset=offset, limit=limit, id_type=id_type)

    if not ids:
        return JsonResponse({chart: {} for chart in queries})

    placeholder = ','.join(map(str, ids))

    for chart, query in queries.items():
        with Engine.begin() as conn:
            cursor = conn.connection.cursor(cursor_factory=DictCursor)
            cursor.execute(query.format(placeholder))
            res = cursor.fetchall()

        if chart == "epiweek":
            results[chart] = {
                f"{row['se_notif']:02d}{row['ano_notif']}": row['count']
                for row in res
            }

        if chart == "cs_sexo":
            results[chart] = {row[chart]: row['count'] for row in res}

        if chart in ["criterio", "municipio_geocodigo"]:
            results[chart] = {str(row[chart]): row['count'] for row in res}

    return JsonResponse(results)
