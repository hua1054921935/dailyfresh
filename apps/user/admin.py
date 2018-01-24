from django.contrib import admin
from apps.user.models import *
# Register your models here.
class GoodssssInfoAdmin(admin.ModelAdmin):
    list_display = ['id']

admin.site.register(GoodssssInfo,GoodssssInfoAdmin)
admin.site.register(Address)