import os
import re
import io
import csv
from pathlib import Path

import pandas as pd
from simpledbf import Dbf5
from dbfread import DBF

from django.http import JsonResponse, HttpResponse
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from celery.result import AsyncResult
from django.views import View
from django.contrib import messages
from django.conf import settings

from .sinan.utils import EXPECTED_FIELDS, REQUIRED_FIELDS
from .tasks import sinan_split_by_uf_or_chunk
from .models import UFs, Diseases


User = get_user_model()


class UploadSINAN(View):
    template_name = "upload.html"

    def get(self, request):
        if not request.user.is_staff:
            return redirect("dados:main")
        context = {}

        context["ufs"] = UFs.choices
        context["diseases"] = Diseases.choices

        return render(request, self.template_name, context)


class ProcessSINAN(View):
    template_name = "process-file.html"

    def get(self, request):
        if not request.user.is_staff:
            messages.error(request, "Unauthorized")
            return redirect("dados:main")

        context = {}

        user_id = request.GET.get("user_id", None)
        disease = request.GET.get("disease", None)
        notification_year = request.GET.get("notification_year", None)
        uf = request.GET.get("uf", None)
        file_path = request.GET.get("file_path", None)
        task_id = request.GET.get("task_id", None)

        if not all(
            [user_id, disease, notification_year, uf, file_path, task_id]
        ):
            messages.error(
                request,
                "Access denied, please use /upload/sinan/ instead",
            )
            return redirect("upload_sinan")

        user = User.objects.get(pk=user_id)

        if request.user != user:
            messages.error(
                request,
                "Access denied, please use /upload/sinan/ instead",
            )
            return redirect("upload_sinan")

        dest_dir = Path(os.path.splitext(file_path)[0])
        dest_dir.mkdir(exist_ok=True)

        context["user_id"] = user_id
        context["disease"] = disease
        context["notification_year"] = notification_year
        context["uf"] = uf
        context["task_id"] = task_id
        context["dest_dir"] = str(dest_dir)

        from pprint import pprint
        pprint(context)

        return render(request, self.template_name, context)


def sinan_upload_file(request):
    if not request.user.is_staff:
        return JsonResponse(
            {'error': 'Unauthorized'}, status=403
        )

    if request.method == "POST" and request.FILES["file"]:
        file = request.FILES["file"]

        dest_dir = Path(os.path.join(settings.MEDIA_ROOT, "upload/sinan/"))

        dest_dir.mkdir(exist_ok=True, parents=True)

        file_path = dest_dir / file.name
        with open(file_path, 'wb') as dest:
            for chunk in file.chunks():
                dest.write(chunk)

        return JsonResponse({'file_path': str(file_path)})

    return JsonResponse(
        {'error': 'POST request with file required'}, status=400
    )


def sinan_chunk_uploaded_file(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if request.method == "POST":
        file = Path(request.POST.get("file_path"))

        if not file.exists():
            return JsonResponse({'error': 'File not found'}, status=404)

        dest_dir = Path(os.path.splitext(str(file))[0])

        dest_dir.mkdir(exist_ok=True, parents=True)

        result = sinan_split_by_uf_or_chunk.delay(  # pyright: ignore
            file_path=str(file),
            dest_dir=str(dest_dir),
            by_uf=False
        )

        request.session['task_id'] = result.id

        return JsonResponse({'task_id': result.id}, status=200)

    if request.method == "GET":
        task_id = request.GET.get("task_id")

        if 'task_id' in request.session:
            task_id = request.session['task_id']

            task = AsyncResult(task_id)

            if task.status == "SUCCESS":
                _, chunks_dir = task.get()  # pyright: ignore
                return JsonResponse(
                    {'task_status': task.status, 'chunks_dir': chunks_dir}
                )
            else:
                return JsonResponse({'task_status': task.status})

        else:
            return JsonResponse({'error': f'Unknown task ID'}, status=400)

    return JsonResponse({'error': 'Request error'}, status=404)


def sinan_watch_for_uf_chunks(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if request.method == "GET":
        dest_dir = Path(request.GET.get("dest_dir")).absolute()

        if not dest_dir.exists() or not dest_dir.is_dir():
            return JsonResponse({'error': 'Incorrect `dest_dir`'}, status=404)

        regexp = re.compile(r"|".join(list(map(str, UFs))) + r"\.csv\.gz")
        uf_files: list[dict] = [
            {
                "file": f.name,
                "uf": f.name[:2],
                "size": os.path.getsize(str(f))
            }
            for f in dest_dir.glob("*.csv.gz")
            if regexp.match(f.name)
        ]

        return JsonResponse({"files": uf_files}, status=200)

    return JsonResponse({'error': 'Request error'}, status=404)


def sinan_check_csv_columns(request):
    if not request.user.is_staff:
        return redirect('dados:main')

    if request.method == "POST" and request.FILES["truncated-file"]:
        file = request.FILES["truncated-file"]
        file_data = file.read()
        context = {}

        if (
            file.name.lower().endswith((".csv.gz", ".csv"))
            or file.content_type == "text/csv"
        ):
            try:
                sniffer = csv.Sniffer()
                sep = sniffer.sniff(file_data.decode('utf-8')).delimiter

                columns = pd.read_csv(
                    io.BytesIO(file_data),
                    nrows=10,
                    sep=sep
                ).columns.to_list()

                if not all([c in columns for c in REQUIRED_FIELDS]):
                    return JsonResponse({'error': (
                        "Required field(s): "
                        f"{list(set(REQUIRED_FIELDS).difference(set(columns)))} "
                        "not found in data file"
                    )}, status=400)

                if not all([c in columns for c in EXPECTED_FIELDS.values()]):
                    context["warning"] = (
                        "Expected field(s): "
                        f"{list(set(EXPECTED_FIELDS.values()).difference(set(columns)))} "
                        "not found in data file, and will be  filled with None"
                    )

                context['file'] = file.name

                context['columns'] = columns

                return JsonResponse(context, status=200)

            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)

        return JsonResponse(
            {'error': f'Could not extract {file.name} columns'}, status=400
        )

    return JsonResponse(
        {'error': 'POST request with file required'},
        status=400
    )
