from django.shortcuts import render,redirect
from django.views.generic import View
from django.http import JsonResponse
from django.core.urlresolvers import reverse
from apps.indent.models import OrderGoods,OrderInfo
from apps.user.models import Address
from apps.goods.models import GoodsSKU
from django.conf import settings
from django_redis import get_redis_connection
from utils.mixin import LoginRequiredMixin
from datetime import datetime
from alipay import AliPay

from django.db import transaction

# Create your views here.
# class OrderPlaceView(View):

class OrderPlaceView(LoginRequiredMixin,View):

    def post(self,request):
        '''显示'''
        # 获取登录用户
        user = request.user

        # 获取用户要购买商品的ids
        # request.POST->QueryDict类的对象，允许一个名字对应多个值
        # 去多个值的时候，需要调用对象的getlist方法
        sku_ids=request.POST.getlist('sku_ids')
        # 参数校验
        if not all([sku_ids]):
            return redirect(reverse('cars:show'))

            # 获取用户的收货地址信息
        addrs=Address.objects.filter(user=user)
        # 获取redis链接
        conn=get_redis_connection('default')

        cart_key='cart_%d' %user.id

        skus=[]
        total_count=0
        total_amount=0
        # 获取商品信息
        for sku_id in sku_ids:
            sku=GoodsSKU.objects.get(id=sku_id)
            # 从redis中获取用户要购买的商品的数量
            # hget(key, field): 获取redis中sku_id属性的值
            count=conn.hget(cart_key,sku_id)
            # 计算购买商品的小计
            amount=int(count)*sku.price
            # 给sku对象增加属性count和amont
            # 分别保存用户要购买商品的数目和小计
            sku.amount=amount
            sku.count=count
            # 追加商品
            skus.append(sku)
            # 累加计算用户要购买的商品的总件数和总金额
            total_count+=int(count)
            total_amount+=amount
        # 运费
        transit_price=10
        # 实付款
        total_pay=total_amount+transit_price
        # 组织上下文
        sku_ids = ','.join(sku_ids)  # 1,4
        context={
            'addrs':addrs,
            'skus':skus,
            'total_pay':total_pay,
            'total_count':total_count,
            'total_amount':total_amount,
            'sku_ids':sku_ids,
            'transit_price':transit_price
        }
        return render(request,'user/place_order.html',context)
#/indent/commit
class OrderCommitView(View):

    def post(self,request):
        '''订单创建'''
        # 判断用户是否登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        addr_id=request.POST.get('addr_id')
        pay_method=request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')  # 1,4


        # 参数校验
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 校验地址信息
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '地址信息错误'})
        # 校验支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 3, 'errmsg': '支付方式非法'})
        # 组织生成订单参数
        # 订单id: 20180121120530 + 用户id
        order_id=datetime.now().strftime('%Y%m%d%H%M%S')+str(user.id)

        # 运费: 10
        transit_price = 10
        # 订单中商品的总数目和总金额
        total_count = 0
        total_price = 0
        # 设置mysql事务的保存点
        # sid=transaction.savepoint()
        # todo: 向df_order_info表中添加一条记录
        try:
            order =OrderInfo.objects.create(order_id=order_id,
                                            addr=addr,
                                            user=user,
                                            pay_method=pay_method,
                                            total_count=total_count,
                                            total_price=total_price,
                                            transit_price=transit_price)
            # 创建链接
            conn=get_redis_connection('default')
            # 拼接key
            cart_key = 'cart_%d' % user.id
            sku_ids=sku_ids.split(',')
            # sku_ids = sku_ids.split(',')


            for sku_id in sku_ids:
                # 根据id查询商品的信息
                # print(sku_id)
                try:
                    sku=GoodsSKU.objects.get(id=sku_id)
                    # print(sku.id)

                except GoodsSKU.DoesNotExist:
                    # 事务回滚
                    # transaction.savepoint_rollback(sid)
                    return JsonResponse({'res': 4, 'errmsg': '商品信息错误'})
                # 获取商品的数量
                count=conn.hget(cart_key,sku_id)

                # 判断商品的库存
                if int(count) > sku.stock:
                    # 事务回滚
                    # transaction.savepoint_rollback(sid)
                    return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})

                # todo: 向df_order_goods表中添加一条记录
                OrderGoods.objects.create(order=order,
                                          sku=sku,
                                          count=int(count),
                                          price=sku.price)
                # todo: 减少对应商品的库存，增加销量
                sku.stock-=int(count)
                sku.sales+=int(count)
                # todo: 累加计算用户要购买的商品的总数目和总金额
                total_count+=int(count)
                total_price+=sku.price*int(count)
            # todo: 更新订单信息记录中的购买的商品的总数目和总金额
            order.total_count=total_count
            order.total_price=total_price
            order.save()
        except Exception as a:
            # transaction.savepoint_rollback(sid)
            return JsonResponse({'res': 7, 'errmsg': '下单失败'})
            # 释放事务保存点sid
            # transaction.savepoint_commit(sid)

            # todo: 删除购物车中对应记录
            # hdel(key, *args)
        conn.hdel(cart_key,*sku_ids)

        # 返回应答
        return JsonResponse({'res': 5, 'message': '订单创建成功'})

class OrderPayView(View):
    """订单支付"""
    def post(self, request):
        """订单支付"""
        # 获取user
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        order_id = request.POST.get('order_id')

        # 参数校验
        if not all([order_id]):
            return JsonResponse({'res': 1, 'errmsg': '参数为空'})

        # 校验订单信息
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          order_status=1,
                                          pay_method=3)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '无效的订单id'})

        # 业务处理: 调用支付宝的下单支付接口
        # 初始化
        alipay = AliPay(
            appid="2016091300499060", # 应用id
            app_notify_url=None,  # 默认回调url
            app_private_key_path=settings.APP_PRIVATE_KEY_PATH, # 应用私钥文件路径
            alipay_public_key_path=settings.ALIPAY_PUBLIC_KEY_PATH,  # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False, True代表沙箱环境
        )

        total_pay = order.total_price + order.transit_price # decimal
        # 调用支付宝alipay.trade.page.pay的接口
        # 电脑网站支付，需要跳转到https://openapi.alipaydev.com/gateway.do? + order_string
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id, # 订单id
            total_amount=str(total_pay), # 订单总金额
            subject='天天生鲜%s'%order_id, # 订单标题
            return_url=None,
            notify_url=None  # 可选, 不填则使用默认notify url
        )

        # 支付页面地址
        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string

        # 返回应答
        return JsonResponse({'res': 3, 'pay_url': pay_url})


# 前端传递的参数: 订单id(order_id)
# 采用ajax post请求
# /order/check
class OrderCheckView(View):
    """支付结果查询"""
    def post(self, request):
        """查询"""
        # 获取user
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        order_id = request.POST.get('order_id')

        # 参数校验
        if not all([order_id]):
            return JsonResponse({'res': 1, 'errmsg': '参数为空'})

        # 校验订单信息
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          order_status=1,
                                          pay_method=3)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '无效的订单id'})

        # 业务处理: 调用支付宝交易查询接口
        # 初始化
        alipay = AliPay(
            appid="2016090800464054",  # 应用id
            app_notify_url=None,  # 默认回调url
            app_private_key_path=settings.APP_PRIVATE_KEY_PATH,  # 应用私钥文件路径
            alipay_public_key_path=settings.ALIPAY_PUBLIC_KEY_PATH,  # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False, True代表沙箱环境
        )

        # 交易查询
        # {
        #     "trade_no": "2017032121001004070200176844", # 支付宝交易号
        #     "code": "10000", # 网关返回码
        #     "invoice_amount": "20.00",
        #     "open_id": "20880072506750308812798160715407",
        #     "fund_bill_list": [
        #         {
        #             "amount": "20.00",
        #             "fund_channel": "ALIPAYACCOUNT"
        #         }
        #     ],
        #     "buyer_logon_id": "csq***@sandbox.com",
        #     "send_pay_date": "2017-03-21 13:29:17",
        #     "receipt_amount": "20.00",
        #     "out_trade_no": "out_trade_no15",
        #     "buyer_pay_amount": "20.00",
        #     "buyer_user_id": "2088102169481075",
        #     "msg": "Success",
        #     "point_amount": "0.00",
        #     "trade_status": "TRADE_SUCCESS", # 交易状态
        #     "total_amount": "20.00"
        # }
        while True:
            response = alipay.api_alipay_trade_query(out_trade_no=order_id)

            # 获取网关返回码
            code = response.get('code')
            # print('code:%s'%code)

            if code == '10000' and response.get('trade_status') == "TRADE_SUCCESS":
                # 获取支付宝交易号
                trade_no = response.get('trade_no')
                # 获取订单支付状态，设置支付宝交易号
                order.order_status = 4 # 待评价
                order.trade_no = trade_no
                order.save()
                # 返回应答
                return JsonResponse({'res': 3, 'message': '支付成功'})
            elif code == '40004' or (code == '10000' and response.get('trade_status') == 'WAIT_BUYER_PAY'):
                # code == '40004' 支付交易还未创建，过一会之后就会创建
                # 等待买家付款，过一会之后再次查询
                import time
                time.sleep(5)
                continue
            else:
                # 支付失败
                return JsonResponse({'res': 4, 'errmsg': '支付失败'})

