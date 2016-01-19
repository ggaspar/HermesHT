from django.conf.urls import patterns, include, url
from django.contrib import admin
from services.views import addCompany,removeCompany,forceRefresh, startServer, stopServer,\
    getStatus, setAutoRefreshDelay,getCompaniesProduction

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^addCompany/([^/]{1,50})/$', addCompany),
    url(r'^removeCompany/([^/]{1,50})/$', removeCompany),
    url(r'^forceRefresh/$', forceRefresh),
    url(r'^startServer/$', startServer),
    url(r'^stopServer/$', stopServer),
    url(r'^getStatus/$', getStatus),
    url(r'^setAutoRefreshDelay/([0-9]{1,5})/$', setAutoRefreshDelay),
    url(r'^getCompaniesProduction/([0-9]{4}-[0-9]{1,2}-[0-9]{1,2})/([0-9]{4}-[0-9]{1,2}-[0-9]{1,2})/([A-Z]{1})/$',
        getCompaniesProduction),

)
