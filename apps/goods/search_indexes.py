from haystack import indexes
from apps.goods.models import GoodsSKU

class GoodsSKUIndex(indexes.SearchIndex,indexes.Indexable):
    # 索引字段， use_template=True说明需要在一个文件中指定根据表中哪些字段的内容建立索引数据
    text=indexes.CharField(document=True,use_template=True)

    def get_model(self):
        # 返回模型类
        return GoodsSKU
    # index_queryset返回哪些数据，就会建立对应的索引
    def index_queryset(self, using=None):
        return self.get_model().objects.all()