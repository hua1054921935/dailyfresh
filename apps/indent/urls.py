
from django.conf.urls import include, url
from django.contrib import admin
from apps.indent.views import OrderPlaceView,OrderCommitView,OrderPayView,OrderCheckView
# from apps.indent.views import OrderPlaceView,OrderCommitView

urlpatterns = [
url(r'^place$',OrderPlaceView.as_view(),name='place'),
url(r'^commit$',OrderCommitView.as_view(),name='commit'),
url(r'^pay$',OrderPayView.as_view(),name='pay'),
url(r'^check$',OrderCheckView.as_view(),name='check')
]
