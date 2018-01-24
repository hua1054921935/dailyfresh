from django.views.generic import View
from django.contrib.auth.decorators import login_required



class LoginRequirdView(View):
    @classmethod
    def as_view(cls, **initkwargs):
        view=super(LoginRequirdView,cls).as_view(**initkwargs)
        return login_required(view)

class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls, **initkwargs):
        # 调用View类中as_view方法
        view = super(LoginRequiredMixin, cls).as_view(**initkwargs)

        # 调用login_required装饰器
        return login_required(view)
