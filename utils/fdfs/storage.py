from django.core.files.storage import Storage
from django.conf import settings
from fdfs_client.client import Fdfs_client
import os

from django.db.models.fields.files import ImageFieldFile

# 当通过后台管理页面上传文件时，保存文件的时候Storage类中的save方法会被调用
# 在save方法中调用了文件存储类的_save方法来实现文件的保存
# _save方法的返回值最终会被保存在表的image字段中

# diango在保存文件时，调用save方法之前，会先调用exists(判断文件是否已存在,
# 防止同名文件被覆盖)


class FDFSStorage(Storage):
    """FDFS文件存储类"""
    def __init__(self, client_conf=None, nginx_url=None):
        """初始化"""
        if client_conf is None:
            client_conf = settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf

        if nginx_url is None:
            nginx_url = settings.FDFS_NGINX_URL
        self.nginx_url = nginx_url

    # def _open(self, name, mode='rb'):
    #     """打开文件时调用"""
    #     pass

    def _save(self, name, content):
        """保存文件时调用"""
        # name: 上传文件的名称
        # content: 包含上传文件内容的File类的实例对象

        # 创建一个Fdfs_client类的对象
        client = Fdfs_client(self.client_conf)

        # 上传文件到FDFS系统中
        # 获取上传文件内容
        content = content.read()

        # 根据文件的内容上传图片
        # {
        #     'Group name': group_name,
        #     'Remote file_id': remote_file_id, # 返回的文件ID
        #     'Status': 'Upload successed.',
        #     'Local file name': '',
        #     'Uploaded size': upload_size,
        #     'Storage IP': storage_ip
        # } if success else None

        response = client.upload_by_buffer(content)

        if response is None or response.get('Status') != 'Upload successed.':
            # 上传失败，抛出异常
            raise Exception('上传文件到FDFS系统失败')

        # 获取文件id
        file_id = response.get('Remote file_id')

        # 返回文件id
        return file_id

    def exists(self, name):
        """判断文件是否存在"""
        return False

    def url(self, name):
        """返回可访问到文件的url路径"""
        return self.nginx_url + name
