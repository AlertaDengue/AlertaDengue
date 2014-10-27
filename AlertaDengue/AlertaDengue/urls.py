# coding=utf-8
from django.conf.urls import patterns, include, url
from django.contrib import admin
from dados.views import HomePageView, SinanCasesView, AboutPageView, ContactPageView, MapaDengueView, MapaMosquitoView, HistoricoView, AlertaPageView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'AlertaDengue.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^$', AlertaPageView.as_view(), name='alerta'),
    url(r'^alerta-detalhado/$', login_required(HomePageView.as_view()), name='home'),
    url(r'^mapadengue/$', MapaDengueView.as_view(), name='mapadengue'),
    url(r'^mapamosquito/$', MapaMosquitoView.as_view(), name='mapamosquito'),
    url(r'^historico/$', login_required(HistoricoView.as_view()), name='historico'),
    url(r'^informacoes/$', AboutPageView.as_view(), name='about'),
    url(r'^contato/$', ContactPageView.as_view(), name='contact'),
    url(r'^sinan/(\d{4})/(\d{1,2})', SinanCasesView.as_view(), name='sinan'),
    url(r'^admin/', include(admin.site.urls)),
) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
