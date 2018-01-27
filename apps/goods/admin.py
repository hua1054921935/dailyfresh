from django.contrib import admin
from django.core.cache import cache
from apps.goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner
# Register your models here.


class BaseAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        """新增或更新时调用"""
        # 调用父类的方法执行更新，新增操作
        super().save_model(request, obj, form, change)

        # 附加操作：发出generate_static_index_html任务
        print('发出generate_static_index_html任务')
        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()

        # 附加操作: 清除首页缓存数据
        cache.delete('index_page_data')

    def delete_model(self, request, obj):
        """删除时调用"""
        # 调用父类的方法执行删除操作
        super().delete_model(request, obj)

        # 附加操作：发出generate_static_index_html任务
        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()

        # 附加操作: 清除首页缓存数据
        cache.delete('index_page_data')


class GoodsTypeAdmin(BaseAdmin):
    pass


class IndexGoodsBannerAdmin(BaseAdmin):
    pass


class IndexPromotionBannerAdmin(BaseAdmin):
    pass


class IndexTypeGoodsBannerAdmin(BaseAdmin):
    pass


admin.site.register(GoodsType, GoodsTypeAdmin)
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)
admin.site.register(IndexTypeGoodsBanner, IndexTypeGoodsBannerAdmin)
