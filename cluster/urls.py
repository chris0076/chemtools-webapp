from django.conf.urls import patterns, url
from django.contrib import admin


admin.autodiscover()
urlpatterns = patterns('cluster.views',
                       url(r"^$", "job_index"),
                       url(r"^running.json$", "get_job_list"),
                       url(r"^(?P<cluster>[^/]*)/$", "cluster_job_index"),
                       url(r"^(?P<cluster>[^/]*)/(?P<jobid>[0-9]*)/$",
                           "job_detail"),
                       url(r"^(?P<cluster>[^/]*)/kill/$", "kill_job"),
                       )
