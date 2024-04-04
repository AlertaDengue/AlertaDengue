from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages


class UploadSINAN(View):
    template_name = "upload.html"

    def get(self, request):
        if not request.user.is_staff:
            return redirect("dados:main")
        return render(request, self.template_name)

    def post(self, request):
        if request.method == 'POST':
            files = request.FILES.getlist('files')

            messages.success(
                request, f'Successfully uploaded {len(files)} files.')
            return redirect('upload')

        return redirect('upload')
