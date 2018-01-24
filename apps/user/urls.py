
from django.conf.urls import include, url
from django.contrib import admin
from apps.user.views import *
from django.contrib.auth.decorators import login_required


urlpatterns = [
    url(r'^register',RegisterView.as_view(),name='register'),
    url(r'^active/(?P<token>.*)$',ActiveView.as_view(),name='active'),
    url(r'^login',LoginView.as_view(),name='login'),
    url(r'^loginout$',LoginoutView.as_view(),name='loginout'),
    url(r'^userinfo$',login_required(UserInfoView.as_view()),name='userinfo'),
    url(r'^userorder/(?P<page>\d+)$',login_required(UserOrderView.as_view()),name='userorder'),
    url(r'^usersite$',login_required(UserSiteView.as_view()),name='usersite')

]
