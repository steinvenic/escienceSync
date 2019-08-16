#!/usr/bin/env python
# encoding: utf-8
"""
@version: python2.7
@author: ‘eric‘
@license: Apache Licence
@contact: steinven@qq.com
@site: 00123.ml:8000
@software: PyCharm
@file: escience.py
@time: 18/4/24 下午2:41
"""
import configparser
import json
import os
import sys
from contextlib import closing
from urllib.parse import unquote

import requests
from loguru import logger

from process_bar import ProgressBar

requests.packages.urllib3.disable_warnings()
conf = configparser.ConfigParser()
conf.read('conf.cfg')
userName = conf.get('user_info', 'userName')
passwd = conf.get('user_info', 'passwd')
download_dir = conf.get('file', 'download_path')
current_dir = os.path.dirname(os.path.abspath(__file__))
all_files = []
class escience:
    def __init__(self, userName, passwd):
        self.userName = userName
        self.passwd = passwd
        self.session = requests.session()
        self.header = {'Accept': 'application/json, text/javascript, */*; q=0.01',
                       'Accept-Encoding': 'gzip, deflate',
                       'Accept-Language': 'zh-CN,zh;q=0.9',
                       'Connection': 'keep-alive',
                       "Content-Type":"application/x-www-form-urlencoded",
                       'Host': 'ddl.escience.cn',
                       'Origin': 'http://ddl.escience.cn',
                       'Referer': 'http://ddl.escience.cn/pan/list',
                       'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) '
                                     'AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 '
                                     'Safari/7046A194A',
                       'X-Requested-With': 'XMLHttpRequest'}

    def login_page(self):
        url = 'https://passport.escience.cn/oauth2/authorize'
        params = {
            "response_type": "code",
            "redirect_uri": "http%3A%2F%2Fddl.escience.cn%2Fsystem%2Flogin%2Ftoken",
            "client_id": "87142",
            "theme": "full",
            "state": "http%3A%2F%2Fddl.escience.cn%2Fpan%2Flist"
        }
        r = self.session.get(url, params=params, headers=self.header, verify=False)
        if r.status_code!=200:
            logger.error("请求登录界面失败，请检查是否开启了代理或其它因素，导致连接不安全！")
            sys.exit(0)
        logger.debug('login_page Response:' + r.text)

    def auth(self):
        url = 'https://passport.escience.cn/oauth2/authorize?client_id=87142&redirect_uri=http://' \
              'ddl.escience.cn/system/login/token&response_type=code&state=http://ddl.escience.cn/pan/list&theme=full'
        data = {'act': 'Validate',
                'pageinfo': 'userinfo',
                'password': '%s' % passwd,
                'theme': 'full',
                'userName': '%s' % userName}
        r = self.session.post(url, headers=self.header, data=data, verify=False, allow_redirects=False)
        try:
            r_location = r.headers['Location']
            logger.info("登陆成功！")
            return r_location
        except:
            logger.error("登录失败，请检查配置文件中账号、密码是否正确！")
            sys.exit(0)

    def location_302(self):
        location_url = self.auth()
        self.session.post(url=location_url, headers=self.header, allow_redirects=False)
        logger.debug('访问重定向地址：' + location_url)

    def get_all_file(self, path):
        global all_files

        url = 'http://ddl.escience.cn/pan/list?func=query'
        data = 'path={}&sortType=&tokenKey=1565968600524&keyWord='.format(path)
        r = self.session.post(url=url, headers=self.header, data=data)
        if 'children' in  r.text:
            r_dict = json.loads(r.text)['children']  # 搜索到的结果集
            for i in r_dict:
                if i['itemType'] != 'Folder':
                    global all_files
                    all_files.append(i['rid'])
                else:
                    self.get_all_file(i['rid'])
        return all_files

if __name__ == '__main__':
    e = escience(userName, passwd)
    e.login_page()
    e.location_302()
    a = e.get_all_file('')
    for i in a:
        url = 'http://ddl.escience.cn/pan/download?path=%s' % i
        logger.info('远程文件链接：' + url)
        with closing(e.session.get(url, headers=e.header, verify=False, stream=True)) as response:
            chunk_size = 1024  # 单次请求最大值
            content_size = int(response.headers['content-length'])  # 内容体总大小
            file_name = '%s' % unquote(i.split('%2F')[-1])
            full_file_path = unquote(i)
            full_dir_path = os.path.dirname(os.path.abspath(__file__))+full_file_path.replace(r'/','\\').strip().replace(file_name,'')
            if not os.path.exists(full_dir_path):
                os.makedirs(full_dir_path)
            progress = ProgressBar(file_name, total=content_size,
                                   unit="KB", chunk_size=chunk_size, run_status="正在下载", fin_status="下载完成")
            with open(full_dir_path+file_name, "wb") as file:
                for data in response.iter_content(chunk_size=chunk_size):
                    file.write(data)
                    progress.refresh(count=len(data))
            file.close()
            logger.info('文件下载路径【%s】' % download_dir)
