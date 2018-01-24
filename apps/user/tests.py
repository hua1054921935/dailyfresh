from django.test import TestCase
from apps.user.models import *
# Create your tests here.
# 设置普通用户
user=User.objects.create_user('python','python@163.com','123456')

user.save()