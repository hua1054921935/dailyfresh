from django.shortcuts import render,redirect
from django.views.generic import View
from django.core.cache import cache
from django.core.urlresolvers import reverse
# Create your views here.
from apps.goods.models import GoodsSKU, GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner
from apps.indent.models import OrderGoods
from django_redis import get_redis_connection


class IndexView(View):
    """首页"""
    def get(self, request):
        """显示"""
        # 先尝试从缓存中获取
        context=cache.get('index_page_data')
        if context is None:
            # 获取商品分类信息
            types = GoodsType.objects.all()
            # 获取首页轮播商品的信息
            index_banner = IndexGoodsBanner.objects.all().order_by('index')
            # 获取首页促销活动信息
            promotion_banner = IndexPromotionBanner.objects.all().order_by('index')
            # 获取首页分类商品展示的信息
            for type in types:
                # 查询type种类首页展示的文字商品的信息
                title_banner = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')
                # 查询type种类首页展示的图片商品的信息
                image_banner = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')

                # 给type对象增加属性title_banner和image_banner
                # 分别保存type中类首页展示的文字商品信息和图片商品的信息
                type.title_banner = title_banner
                type.image_banner = image_banner

            # 获取登录用户购物车中商品的条目数
            cart_count = 0
            # 获取user

            user = request.user
            if user.is_authenticated():
                # 用户已登录
                conn = get_redis_connection('default') # StrictRedis
                # 拼接key
                cart_key = 'cart_%s'%user.id
                cart_count = conn.hlen(cart_key)

            # 组织模板上下文
            context = {'types': types,
                       'index_banner': index_banner,
                       'promotion_banner': promotion_banner,
                       'cart_count': cart_count}
            # 设置缓存
            cache.set('index_page_data', context, 3600)
            # 获取登录用户购物车中商品的条目数
            # 获取user
        user = request.user
        if user.is_authenticated():
            # 用户已登录
            conn = get_redis_connection('default')  # StrictRedis
            # 拼接key
            cart_key = 'cart_%s' % user.id
            cart_count = conn.hlen(cart_key)
            context.update(cart_count=cart_count)
        # 使用模板
        return render(request, 'user/index.html',context)


class DetailView(View):
    '''详情页'''
    def get(self,request,sku_id):
        # 获取商品分类详情
        types=GoodsType.objects.all()
        # 获取商品的详情信息
        try:
            sku=GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在跳到首页
            return redirect(reverse('goods:index'))
        # 获取商品的评论信息
        order_skus=OrderGoods.objects.filter(sku=sku).exclude(comment='').order_by('-update_time')
        # 获取和商品同一种类的2个新品信息
        new_skus=GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]
        # 获取和商品同一个SPU其他规格商品
        same_spu_skus=GoodsSKU.objects.filter(goods=sku.goods).exclude(id=sku_id)
        # 获取和商品同一个SPU其他规格商品
        cart_count=0
        # 获取user
        user=request.user
        if user.is_authenticated():
            # 用户已登录
            conn=get_redis_connection('default')
            # 拼接key 作为每个用户的购物车记录
            cart_key='cart_%s' %user.id
            cart_count=conn.hlen(cart_key)
            history_key='history_%s' %user.id
            # # lem：如果存在元素则移除，如果不存在什么都不做
            conn.lrem(history_key,0,sku_id)
            # 将sku_id添加到列表左侧
            conn.lpush(history_key,sku_id)
            # 保留列表的前5个商品的id
            conn.ltrim(history_key, 0, 4)
            context={
                'types':types,
                'sku':sku,
                'new_skus':new_skus,
                'same_spu_skus':same_spu_skus,
                'cart_count':cart_count
            }
            return render(request,'user/detail.html',context)

# 前端需要传递的参数: 种类id 页码 排序方式
# get: /list?type_id=种类id&page=页码&sort=排序方式
# url捕获: /list/种类id/页码/排序方式
# url: /list/种类id/页码?sort=排序方式
# /list/7
class ListView(View):
    def get(self,request,type_id,page):
        '''显示'''
        # 获取全部商品分类的信息
        types=GoodsType.objects.all()
        try:
            type=GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            return redirect(reverse('goods:index'))
        # 获取排序方式 并 获取type分类的商品的列表信息
        # sort=='default': 按照默认顺序(商品id)进行排序
        # sort=='price': 按照商品的价格(price)进行排序
        # sort=='hot': 按照商品的人气(sales)进行排序
        sort = request.GET.get('sort')
        if sort=='price':
            skus=GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort=='hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('price')
        else:
            sort = 'default'
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')

        # 分页处理
        from django.core.paginator import Paginator
        paginator=Paginator(skus,1)

        # 处理页码
        page=int(page)
        if page>paginator.num_pages:
            page=1
        # 获取分页内容
        skus_page=paginator.page(page)
        num_pages=paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page + 3)
        # 获取type种类两个分页内容
        new_skus=GoodsSKU.objects.filter(type=type).order_by('-create_time')[:2]

        # 获取登录用户购物车中商品的条目数
        cart_count = 0
        # 获取user
        user = request.user
        if user.is_authenticated():
            # 用户已登录
            conn = get_redis_connection('default')  # StrictRedis
            # 拼接key
            cart_key = 'cart_%s' % user.id
            cart_count = conn.hlen(cart_key)

        # 组织模板上下文
        context = {'types': types,
                   'type': type,
                   'skus_page': skus_page,
                   'new_skus': new_skus,
                   'cart_count': cart_count,
                   'sort': sort,
                   'pages': pages}
        return render(request,'user/list.html',context)








