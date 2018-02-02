from django.views.generic.base import TemplateView
# local
from .settings import MAPSERVER_URL, STATIC_ROOT, STATICFILES_DIRS

import json
import os


class MapaDengueView(TemplateView):
    template_name = 'mapadengue.html'

    def get_context_data(self, **kwargs):
        context = super(MapaDengueView, self).get_context_data(**kwargs)
        return context


class MapaMosquitoView(TemplateView):
    template_name = 'mapamosquito.html'

    def get_context_data(self, **kwargs):
        context = super(MapaMosquitoView, self).get_context_data(**kwargs)
        return context


class AboutPageView(TemplateView):
    template_name = 'about.html'

    def get_context_data(self, **kwargs):
        context = super(AboutPageView, self).get_context_data(**kwargs)
        # messages.info(
        #   self.request,
        #   'O site do projeto Alerta Dengue está em construção.')
        return context


class ContactPageView(TemplateView):
    template_name = 'contact.html'

    def get_context_data(self, **kwargs):
        context = super(ContactPageView, self).get_context_data(**kwargs)
        # messages.info(
        #   self.request,
        #   'O site do projeto Alerta Dengue está em construção.')
        return context


class JoininPageView(TemplateView):
    template_name = 'joinin.html'

    def get_context_data(self, **kwargs):
        context = super(JoininPageView, self).get_context_data(**kwargs)
        # messages.info(
        #   self.request,
        #   'O site do projeto Alerta Dengue está em construção.')
        return context


class PartnersPageView(TemplateView):
    template_name = 'partners.html'

    def get_context_data(self, **kwargs):
        context = super(PartnersPageView, self).get_context_data(**kwargs)
        return context


class DataPublicServicesPageView(TemplateView):
    template_name = 'data_public_services.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        service = kwargs['service']
        service_type = (
            None if 'service_type' not in kwargs else kwargs['service_type']
        )

        if service == 'maps':
            _static_root = os.path.abspath(STATIC_ROOT)
            _static_dirs = os.path.abspath(STATICFILES_DIRS[0])

            path_root = (
                _static_root if os.path.exists(_static_root) else
                _static_dirs
            )

            geo_info_path = os.path.join(
                path_root, 'geojson', 'geo_info.json'
            )

            with open(geo_info_path) as f:
                context.update({
                    'mapserver_url': MAPSERVER_URL,
                    'geo_info': json.load(f)
                })
            self.template_name = 'data_public_services_maps.html'
        elif service == 'api':
            if service_type == 'notebook':
                self.template_name = 'data_public_services_api_notebook.html'
            else:
                self.template_name = 'data_public_services_api.html'
        else:
            self.template_name = 'data_public_services.html'

        return context
