from django.shortcuts import render
from utils.mixin import LoginRequiredMixin
from django.http import JsonResponse
from apps.goods.models import GoodsSKU
from django_redis import get_redis_connection
from django.views.generic import View

# Create your views here.

class CartAddView(View):
    def post(self,request):
        # 获取用户登录
        user=request.user
        # print(user.username)
        if not user.is_authenticated():
            return JsonResponse({'res':1,'errmsg':'用户未登录'})
        # 接受参数
        sku_id=request.POST.get('sku_id')

        count=request.POST.get('count')
        # 参数校验
        if not all([sku_id,count]):
            return JsonResponse({'res':2,'errmsg':'参数不完整'})
        # 校验商品id
        try:
            sku=GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res':3,'errmsg':'无商品'})
        # 校验商品数量
        try:
            count=int(count)
        except Exception as a:
            return JsonResponse({'res':4,'errmsg':'数量有无'})

        if count <= 0:
            return JsonResponse({'res': 3, 'errmsg': '商品数目非法'})

        # 业务处理添加购物车记录信息
        conn=get_redis_connection('default')
        # 拼接key
        cart_key = 'cart_%d' % user.id
        # 如果用户的购物车中已经添加过该商品，则商品的数目需要累加
        # hget(key, field): 如果存在field返回是对应值，如果不存在field，返回None
        cart_count = conn.hget(cart_key, sku_id)
        if cart_count:
            cart_count+=int(cart_count)
        if count>sku.stock:
            return JsonResponse({'res':4,'errmsg':'库存不足'})

        # 设置购物车记录中sku_id对应值
        # hset(key, field, value): 如果field存在则更新值，如果不存在则添加field
        conn.hset(cart_key, sku_id, count)
        # 获取用户购物车中商品的条目数
        cart_count = conn.hlen(cart_key)
        return JsonResponse({'res':5,'message':'添加成功','cart_count':cart_count})

class CartInfoView(LoginRequiredMixin,View):
    def get(self,request):
        # 获取登录用户’
        user=request.user
        # 获取redis链接
        conn=get_redis_connection('default')
        #拼接key
        cart_key='cart_%d'%user.id
        # 从redis中获取用户购物车记录
        # hgetall(key): 返回值是一个字典，字典键就是属性，键对应的值就是属性的值
        cart_dict=conn.hgetall(cart_key)
        skus=[]
        total_amount=0
        total_count=0
        for sku_id,count in cart_dict.items():
            # 根据￼|    提交订单sku_id获取商品信息
            sku=GoodsSKU.objects.get(id=sku_id)

            # 计算商品小计
            amount=sku.price*int(count)

            # 给sku对象增加属性count和amount
            # 分别保存用户添加到购物车中商品的数目和商品小计
            sku.count=int(count)
            sku.amount=amount

            # 追加sku
            skus.append(sku)

            # 累加计算所有商品的总件数和总价格
            total_count+=int(count)
            total_amount+=amount
        context = {'skus': skus,
                   'total_count': total_count,
                   'total_amount': total_amount}
        return render(request, 'user/cart.html', context)
class CartUpdateView(View):
    def post(self,request):
        '''更新'''
        user=request.user
        # 判断用户是否存在
        if not user.is_authenticated():
            return JsonResponse({'res':0,'errmsg':'用户未登录'})

        # 接受参数
        sku_id=request.POST.get('sku_id')
        count=request.POST.get('count')

        # 参数校验
        if not all([sku_id,count]):
            return  JsonResponse({'res':1,'errmsg':'参数不完整'})

        # 校验id
        try:
            sku=GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res':2,'errmsg':'商品不存在'})

        # 校验商品的数量count
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 3, 'errmsg': '商品数目非法'})

        if count<=0:
            return JsonResponse({'res':3,'errmsg0':'商品数目非法'})

        # 业务处理：更新用户购物车记录信息
        # 获取链接
        conn=get_redis_connection('default')

        # 拼接key
        cart_key='cart_%d' %user.id

        # 判断库存
        if count>sku.stock:
            return JsonResponse({'res':4,'errmsg':'库存不足'})
        # 更新数据
        conn.hset(cart_key,sku_id,count)


        # 计算用户购物车中商品的总件数
        # hvals(key): 返回所有属性的值，返回的是一个列表
        cart_vals = conn.hvals(cart_key)
        cart_count=0
        for val in cart_vals:
            cart_count+=int(val)

        return JsonResponse({'res':5,'message':'更新成功','cart_count':cart_count})


class CartDeleteView(View):
    def post(self,request):
        """删除"""
        # 获取登录用户
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        sku_id = request.POST.get('sku_id')

        # 参数校验
        if not all([sku_id]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 校验商品id
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '商品不存在'})

        # 业务处理：删除用户的购物车记录
        # 获取链接对象
        conn = get_redis_connection('default')

        # 拼接key
        cart_key = 'cart_%d' % user.id

        # 删除redis中用户的购物车记录
        # hdel(key, *args): 删除hash中对应属性和值
        conn.hdel(cart_key, sku_id)

        # 计算用户购物车中商品的总件数
        # hvals(key): 返回所有属性的值，返回的是一个列表
        cart_vals = conn.hvals(cart_key)
        cart_count = 0

        for val in cart_vals:
            cart_count += int(val)

        # 返回应答
        return JsonResponse({'res': 3, 'cart_count': cart_count, 'message': '删除成功'})




