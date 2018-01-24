from django.shortcuts import render,redirect
from django.views.generic import View
from django.core.urlresolvers import reverse
import re
from django.contrib.auth import authenticate,login,logout
from django.http import HttpResponse
from django.core.mail import send_mail
from apps.user.models import *
from itsdangerous import Serializer
from django.conf import settings
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from celery_tasks.tasks import send_mail_register
from django_redis import get_redis_connection
from apps.goods.models import GoodsSKU
from apps.indent.models import OrderGoods,OrderInfo

# Create your views here.


class RegisterView(View):
    def get(self,request):
        return render(request,'user/register.html')


    def post(self,request):
    # 接收数据
        username=request.POST.get('user_name')
        password=request.POST.get('pwd')
        email=request.POST.get('email')
    # 进行数据校验
        if not all([username,password,email]):
            return render(request,'user/register.html',{'errmsg':'数据不完整更'})
    # 校验邮箱
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'user/register.html', {'errmsg': '邮箱格式不正确'})
    # 校验是否存在用户
        try:
            user=User.objects.get(username=username)
        except User.DoesNotExist:
            user=None
        if user:
            return render(request, 'user/register.html', {'errmsg': '用户已存在'})
    # 业务处理
        user = User.objects.create_user(username, email, password)
        user.is_active=1
        user.save()
    # 注册成功需要通过邮箱返回激活链接
    # 使用itsdangerous生成激活的token信息
        seeializer=Serializer(settings.SECRET_KEY,3600)
        info={'confirm':user.id}
    # 进行加密
        token=seeializer.dumps(info)
    # 转换类型
        token = token.decode()
    # 组织邮件内容
        send_mail_register(email,username,token)
    # 返回应答
        return redirect(reverse('goods:index'))



class ActiveView(View):
    def get(self,request,token):

        #进行解密
        seeializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info=seeializer.loads(token)

            user_id=info['confirm']
            user=User.objects.get(id=user_id)
            user.is_active=1
            user.save()
            return redirect(reverse('user:login'))
        except SignatureExpired as f:
            return HttpResponse('<h1>链接以失效')

class LoginView(View):
    def get(self,request):
        if 'username' in request.COOKIES:
            username=request.COOKIES['username']
            checked='checked'
        else:
            username=''
            checked=''
        return render(request,'user/login.html',{'username':username,'checked':checked})

    def post(self,request):
        #获取数据
        username=request.POST.get('username')
        password=request.POST.get('pwd')

        # 进行验证
        if not all([username,password]):
            return render(request,'user/login.html',{'errmsg':'输入不能为卡'})
        # 业务处理
        # 登录验证
        # 根据用户名和密码查找信息
        user=authenticate(username=username,password=password)

        if user is not None:
        #     帐号密码正确
            if user.is_active:
                #帐号已激活
                #记住状态
                login(request,user)
                response = redirect(reverse('goods:index'))
                remember=request.POST.get('remember')
                if remember=='on':
                #     记住用户名
                    response.set_cookie('username',username,max_age=7*24*3600)
                else:
                    response.delete_cookie('username')
                return response
            else:
                return render(request,'user/login.html',{'errmsg':'帐号未激活'})
        else:
            return render(request,'user/login.html',{'errmsg':'帐号不存在请注册'})

class LoginoutView(View):
    def get(self,request):
        logout(request)
        return redirect(reverse('user:login'))

class UserInfoView(View):
    """用户中心-信息页"""

    def get(self, request):
        """显示"""
        # 获取登录的用户
        user = request.user

        # 获取用户的收货地址信息
        address = Address.objects.get_deafult_adree(user=user)


        # 获取用户的最近浏览商品信息
        # from redis import StrictRedis
        # conn = StrictRedis(host='172.16.179.142', port='6379', db=12)

        # get_redis_connection返回值是一个StrictRedis类的对象
        conn = get_redis_connection('default')
        # 拼接list的key
        history_key = 'history_%d' % user.id

        # 获取用户最新浏览的5个商品的id
        sku_ids = conn.lrange(history_key, 0, 4)  # [2,1,3,4,5]

        # 根据id获取商品的信息 select ... from table_name id in (2,1,3,4,5)
        # skus = GoodsSKU.objects.filter(id__in=sku_ids)
        #
        # 调整顺序
        # skus_li = []
        # for sku_id in sku_ids:
        #     for sku in skus:
        #         if sku.id == int(sku_id):
        #             skus_li.append(sku)

        skus = []
        for sku_id in sku_ids:
            # 根据sku_id获取商品的信息
            sku = GoodsSKU.objects.get(id=sku_id)
            # 追加元素
            skus.append(sku)

        # 组织模板上下文
        context = {'page': 'user',
                   'address': address,
                   'skus': skus}

        # 使用模板
        return render(request, 'user/user_center_info.html', context)


# /user/order/页码
# class UserOrderView(View):
# class UserOrderView(LoginRequiredView):

class UserOrderView(View):
    """用户中心-订单页"""
    def get(self, request, page):
        """显示"""
        # 获取登录用户
        user = request.user
        # 获取用户的订单信息
        orders = OrderInfo.objects.filter(user=user).order_by('-create_time')


        # 获取用户的每个订单商品的信息
        for order in orders:
            # 获取order订单商品的信息
            order_skus = OrderGoods.objects.filter(order=order)
            print(order_skus)

            # 遍历order_skus计算订单中每个商品的小计
            for order_sku in order_skus:
                # 计算商品的小计
                amount = order_sku.count * order_sku.price

                # 给order_sku增加属性amount，保存订单商品的小计
                order_sku.amount = amount

            # 获取订单状态标题
            order.status_name = OrderInfo.ORDER_STATUS[order.order_status]

            # 计算订单实付款
            order.total_pay = order.total_price + order.transit_price

            # 给order增加属性order_skus，保存订单商品的信息
            order.order_skus = order_skus


        # 分页处理
        from django.core.paginator import Paginator
        paginator = Paginator(orders, 1)

        # 校验页码
        page = int(page)
        if page > paginator.num_pages:
            page = 1

        # 获取第page页的内容，得到Page对象
        order_page = paginator.page(page)


        # 页码过多时页面上最多显示5个页码
        # 1. 分页之后总页数不足5页，显示全部页码
        # 2. 当前是前3页，显示1-5页
        # 3. 当前是后3页，显示后5页
        # 4. 其他情况，显示当前页前2页，当前页，当前页后2页
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page + 3)

        # 组织上下文
        context = {'order_page': order_page,
                   'pages': pages,
                   'page': 'order'}

        return render(request, 'user/user_center_order.html', context)

class UserSiteView(View):
    def get(self,request):
        user=request.user
        address= Address.objects.get_deafult_adree(user)
        context={'page': 'address',
                   'address': address}
        return render(request,'user/user_center_site.html',context)

    def post(self,request):
        # 接受数据
        recever=request.POST.get('recever')
        adree=request.POST.get('adree')
        zb_code = request.POST.get('zb_code')
        phone = request.POST.get('phone')
        #进行验证

        if not all([recever,adree,phone]):
           return  render(request,'user/user_center_site.html',{'errmsg':'数据不完整'})
        # 判断用户存在默认地址
        user=request.user
        address = Address.objects.get_deafult_adree(user)
        is_default = True
        if address:
            is_default=False

            #添加新的地址
        Address.objects.create(user=user,receiver=recever,addr=adree,zip_code=zb_code,phone=phone,
                               is_default=is_default)
        return redirect(reverse('user:usersite'))

