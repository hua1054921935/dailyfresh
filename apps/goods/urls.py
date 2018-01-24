
from django.conf.urls import include, url
from django.contrib import admin
from  apps.goods.views import IndexView,DetailView,ListView

urlpatterns = [
url(r'^$',IndexView.as_view(),name='index'),
url(r'^goods/(?P<sku_id>\d+)$',DetailView.as_view(),name='detail'),
url(r'^type/(?P<type_id>\d+)/(?P<page>\d+)',ListView.as_view(),name='type')
]
