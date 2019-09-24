from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.conf.urls import handler500, handler403

handler500 = 'magi.views.handler500'
handler403 = 'magi.views.handler403'

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'sample_project.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^', include('magi.urls')),
    url(r'^admin/', include(admin.site.urls)),
)
