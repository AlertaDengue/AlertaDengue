import os
import io
import csv
from pathlib import Path

import pandas as pd
from simpledbf import Dbf5
from dbfread import DBF

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.conf import settings

from .sinan.utils import EXPECTED_FIELDS, REQUIRED_FIELDS
from .models import UFs, Diseases


class UploadSINAN(View):
    template_name = "upload.html"

    def get(self, request):
        if not request.user.is_staff:
            return redirect("dados:main")
        context = {}

        context["ufs"] = UFs.choices
        context["diseases"] = Diseases.choices

        return render(request, self.template_name, context)

    def post(self, request):
        if not request.user.is_staff:
            return redirect("dados:main")
        if request.method == 'POST':
            files = request.FILES.getlist('files')

            messages.success(
                request, f'Successfully uploaded {len(files)} files.')
            return redirect('upload')

        return redirect('upload')


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

        print(file_path)
        return JsonResponse({'file_path': str(file_path)})

    return JsonResponse(
        {'error': 'POST request with file required'}, status=400
    )


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

                print(context)

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
