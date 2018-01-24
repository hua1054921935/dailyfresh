
from django.conf.urls import include, url
from django.contrib import admin


urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^search',include('haystack.urls'),name='search'),
    url(r'^user/', include('apps.user.urls', namespace='user')),
    url(r'^cars/', include('apps.cars.urls', namespace='cars')),
    url(r'^goods/', include('apps.goods.urls', namespace='goods')),
    url(r'^indent/', include('apps.indent.urls', namespace='indent')),

]
