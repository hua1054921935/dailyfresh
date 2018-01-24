from django.conf.urls import include, url

from apps.cars.views import CartInfoView,CartAddView,CartDeleteView,CartUpdateView

urlpatterns = [
url(r'^add$',CartAddView.as_view(),name='add'),
url('^$',CartInfoView.as_view(),name='show'),
url(r'^update$',CartUpdateView.as_view(),name='update'),
url(r'^delete$',CartDeleteView.as_view(),name='delete')
]
