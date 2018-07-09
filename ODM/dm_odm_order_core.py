# -*- coding: utf-8 -*-
import os
<<<<<<< HEAD
import pdb
=======
>>>>>>> 6406e6829f904e3c8a3958c1cc028c344f2e7e0f
import re
import sys
import urllib

import requests
import urllib3
import yaml
# import urllib2
# from datetime import datetime
urllib3.disable_warnings()

# __Author__ = "yushuai"
# __Date__ = '2018/05/10 '

# 配置文件信息，设置为全局
MainPath, MainFile = os.path.split(os.path.realpath(__file__))
YamlFile = os.path.join(MainPath, 'dm_odm_order_core.yaml')


class ReadYaml:

    def __init__(self, sat, sensor):
        # 读取yaml格式配置文件

        if not os.path.isfile(YamlFile):
            print 'Not Found %s' % YamlFile
            sys.exit(-1)

        with open(YamlFile, 'r') as stream:
            cfg = yaml.load(stream)

        dtype = sat + '+' + sensor
        if dtype in cfg['web01'].keys():
            self.user = cfg['web01']['user']
            self.pawd = cfg['web01']['pawd']
            self.mail = cfg['web01']['mail']
            self.urlType = cfg['web01'][dtype]['url_type']
            self.body_data = cfg['web01'][dtype]['body_data']
            self.mail_data = cfg['web01'][dtype]['mail_data']
            self.init_type = '1'
        else:
            self.user = cfg['web02']['user']
            self.pawd = cfg['web02']['pawd']
            self.mail = cfg['web02']['mail']
            self.body_data = cfg['web02'][dtype]['body_data']
            self.confirm_data = cfg['web02'][dtype]['confirm_data']
            self.mail_data = cfg['web02'][dtype]['mail_data']
            self.init_type = '2'


def set_newvalue(datadict, key, value):
    # 对提交表单的data 重新赋值
    for vdict in datadict:
        if key in vdict.keys():
            vdict[key] = value


class WEBORDER01(object):
    # 构造请求数据

    def __init__(self, incfg):

        self.url_open = 'https://www.avl.class.noaa.gov/saa/products/classlogin?resource=%2Fsaa%2Fproducts%2Fwelcome'
        self.url_login = 'https://www.avl.class.noaa.gov/saa/products/j_security_check'
        self.s = requests.Session()
        self.s.verify = False  # 取消安全认证

        # 加headers 伪造请求头。
        self.inCfg = incfg
        self.timeout = 60  # 请求超时时间设置
        self.headerss = {
            'User-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                          ' (KHTML, like Gecko) Chrome/66.0.3359.117 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Host': 'www.avl.class.noaa.gov',
            'Origin': 'https://www.avl.class.noaa.gov',
            'Upgrade-Insecure-Requests': '1',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://www.avl.class.noaa.gov/saa/products/classlogin?resource=%2Fsaa%2Fproducts%2Fwelcome'}

    def get_cookie_token(self):
        # 因为登录时需要先获取csrfToken值，所以先get获取，然后在下方post数据的时候使用。

        page = self.s.get(self.url_open, timeout=self.timeout)
        cookie_value = ''
        for cookie in page.cookies:
            cookie_value = cookie.value
        print 'cookie_value=', cookie_value
        return cookie_value

    def login_fn(self):
        # 开始登陆noaa网站

        csrftoken = self.get_cookie_token()  # 获取网站cookie
        print 'cookie=', csrftoken
        for key in self.headerss:
            self.s.headers[key] = self.headerss[key]
        # self.s.headers['Cookie']='JSESSIONID='+csrfToken
        data = urllib.urlencode(
            {"j_username": self.inCfg.user, "j_password": self.inCfg.pawd})
        req = self.s.post(
            url=self.url_login,
            headers=self.s.headers,
            data=data,
            timeout=self.timeout)
        newcookie = req.headers["set-Cookie"].split(";")[0]
        self.s.headers['Cookie'] = newcookie  # 获得登陆成功的cookie 并加入请求头里

    def get_ordernum(self, stime, etime):
        #  获取订单号

        url_order = 'https://www.avl.class.noaa.gov/saa/prod/orderNow'
        url_type = self.inCfg.urlType
        url_order_num = 'https://www.avl.class.noaa.gov/saa/products/shopping_cart'
        url_datatime = 'https://www.avl.class.noaa.gov/saa/products/welcome'
        url_email = 'https://www.avl.class.noaa.gov/saa/products/shop'
        self.s.headers['Referer'] = url_datatime
        req_datatime = self.s.get(url_type, timeout=self.timeout)
        # 获取对应资料的数据起始、结束时间
        data_start = (re.compile('<input type="hidden" name="data_start" ([\s\S]*?)<input type="hidden"').findall(
            req_datatime.text)[0]).split("=")[-1][:-1]
        data_end = (re.compile('<input type="hidden" name="data_end" ([\s\S]*?)<input type="hidden"').findall(
            req_datatime.text)[0]).split("=")[-1][:-1]
        max_days_val = (re.compile(
            '<input type="hidden" name="max_days_val" ([\s\S]*?)>').findall(req_datatime.text)[0]).split("=")[-1]
        self.s.headers['Referer'] = url_type
        start_date, start_time = stime.split()
        end_date, end_time = etime.split()
        data = []
        # 替换页面返回的信息，用于bodydata封装
        # print self.inCfg.body_data
        set_newvalue(self.inCfg.body_data, 'data_start', data_start)
        set_newvalue(self.inCfg.body_data, 'data_end', data_end)
        set_newvalue(self.inCfg.body_data, 'max_days_val', max_days_val)
        set_newvalue(self.inCfg.body_data, 'start_date', start_date)
        set_newvalue(self.inCfg.body_data, 'start_time', start_time)
        set_newvalue(self.inCfg.body_data, 'end_date', end_date)
        set_newvalue(self.inCfg.body_data, 'end_time', end_time)
        # 字典转list
        for v in self.inCfg.body_data:
            for v1, v2 in v.items():
                data.append((v1, v2))
        data = urllib.urlencode(data)
        response = self.s.post(
            url=url_order,
            headers=self.s.headers,
            data=data,
            timeout=self.timeout)
        self.s.get(url_order_num, timeout=self.timeout)
        size = re.compile(
            '<size>([\s\S]*?)</size>').findall(response.text)[0]  # 获取返回的字节数总大小
        # 替换页面返回的信息，用于maildata封装
        email_data = []
        set_newvalue(self.inCfg.mail_data, 'order_size', size)
        set_newvalue(self.inCfg.mail_data, 'email', self.inCfg.mail)

        # 字典转list
        for v in self.inCfg.mail_data:
            for v1, v2 in v.items():
                email_data.append((v1, v2))
        self.s.headers['Referer'] = url_order_num
        email_data = urllib.urlencode(email_data)
        testt = self.s.post(
            url=url_email,
            headers=self.s.headers,
            data=email_data,
            timeout=self.timeout)  # 发送邮件
        # 正则匹配返回订单号
        orderid = (re.compile(
            'Your confirmation number is:\n([\s\S]*?)<br>').findall(testt.text)[0]).strip()[:-1]
        return orderid


class WEBORDER02(object):
    # 构造请求数据

    def __init__(self, incfg):
        self.url_open = 'https://eosweb.larc.nasa.gov/HORDERBIN/HTML_Start.cgi'
        self.url_data = 'https://eosweb.larc.nasa.gov/HORDERBIN/HTML_Results.cgi'
        self.url_order = 'https://eosweb.larc.nasa.gov/HORDERBIN/HTML_Order.cgi'
        self.url_finish = 'https://eosweb.larc.nasa.gov/HORDERBIN/HTML_Finish.cgi'
        self.s = requests.Session()
        self.s.verify = False  # 取消安全认证
        self.timeout = 60  # 超时时间设置
        self.inCfg = incfg
        # 加headers 伪造请求头。
        self.headerss = {
            'User-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                          ' (KHTML, like Gecko) Chrome/66.0.3359.117 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Host': 'eosweb.larc.nasa.gov',
            'Origin': 'https://eosweb.larc.nasa.gov',
            'Upgrade-Insecure-Requests': '1',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://eosweb.larc.nasa.gov/HORDERBIN/HTML_Login.cgi'}

    def get_cookie_token(self):
        # 因为登录时需要先获取csrfToken值，所以先get获取，然后在下方post数据的时候使用。

        page = self.s.get(self.url_open, timeout=self.timeout)
        cookie_value = ''
        for cookie in page.cookies:
            cookie_value = cookie.value
        return cookie_value

    def login_fn(self):
        #  开始登陆

        csrftoken = self.get_cookie_token()  # 获取cookie
        print 'cookie=', csrftoken
        for key in self.headerss:
            self.s.headers[key] = self.headerss[key]
        data = urllib.urlencode(
            {"Login": self.inCfg.user, "Password": self.inCfg.pawd})
        self.s.post(
            url=self.url_open,
            headers=self.s.headers,
            data=data,
            timeout=self.timeout)

    def get_ordernum(self, stime, etime):
        #  获取订单号

        start_date = stime.split(" ")[0]
        end_date = etime.split(" ")[0]
        data = []
        set_newvalue(self.inCfg.body_data, 'start_date', start_date)  # 数据的开始时间
        set_newvalue(self.inCfg.body_data, 'end_date', end_date)      # 数据的结束时间
        # 字典转list
        for v in self.inCfg.body_data:
            for v1, v2 in v.items():
                data.append((v1, v2))
        self.s.headers['Referer'] = self.url_open
        data = urllib.urlencode(data)
        testt = self.s.post(
            url=self.url_data,
            headers=self.s.headers,
            data=data,
            timeout=self.timeout)  # 提交对应卫星的参数
        data_list_number = re.compile(
            '<input name="gran" type="checkbox" value=([\s\S]*?) >&nbsp;&nbsp;&nbsp').findall(testt.content)

        confirm_data = []
        set_newvalue(self.inCfg.confirm_data, 'ship_email', self.inCfg.mail)
        set_newvalue(self.inCfg.confirm_data, 'start_date', start_date)
        set_newvalue(self.inCfg.confirm_data, 'end_date', end_date)
        for v in self.inCfg.confirm_data:
            for v1, v2 in v.items():
                confirm_data.append((v1, v2))
        for v in data_list_number:
            # print v
            confirm_data.append(('gran', v))
        # print confirm_data
        confirm_data = urllib.urlencode(confirm_data)
        self.s.headers['Referer'] = self.url_data
        response = self.s.post(
            url=self.url_order,
            headers=self.s.headers,
            data=confirm_data,
            timeout=self.timeout)  # 确认卫星数据

        # self.write_to_log('log2',response.content)
        granules = re.compile(
            'name="granules" value= ([\s\S]*?)>').findall(response.content)  # 资料的name
        granules_size = re.compile(
            'name="granule_size" value= ([\s\S]*?)>').findall(response.content)  # 资料的size
        dataset = re.compile(
            'name="dataSet" value= ([\s\S]*?)>').findall(response.content)  # 资料的类型
        dataset_size = re.compile(
            'name="dataSet_size" value= ([\s\S]*?)>').findall(response.content)  # 总的size
        # order_list = re.compile(
        #     'name="order_list" value=([\s\S]*?)>').findall(response.content)  # 资料的对应编号的list
        total = re.compile(
            'name="Total" value=([\s\S]*?)>').findall(response.content)  # 总的size
        self.s.headers['Referer'] = self.url_order
        email_data = []  # 替换form表单对应的值
        set_newvalue(self.inCfg.mail_data, 'email', self.inCfg.mail)
        set_newvalue(self.inCfg.mail_data, 'Total', total)
        set_newvalue(self.inCfg.mail_data, 'dataSet_size', dataset_size)
        set_newvalue(self.inCfg.mail_data, 'dataSet', dataset)
        for v in self.inCfg.mail_data:
            for v1, v2 in v.items():
                email_data.append((v1, v2))
        for k in granules:
            email_data.append(('granules', k))
        for v in granules_size:
            email_data.append(('granule_size', v))
        email_data = urllib.urlencode(email_data)
        response_finish = self.s.post(
            url=self.url_finish,
            headers=self.s.headers,
            data=email_data,
            timeout=self.timeout)  # 发送邮件
        order_number = re.compile(
            'Your order #<b>([\s\S]*?)</b>').findall(response_finish.content)[0]
        return order_number


if __name__ == '__main__':
    ycfg = ReadYaml('JPSS-1', 'VIIRS')
    # ycfg = ReadYaml('CALIPSO', 'CALIOP')
    if ycfg.init_type == '1':
        weborder = WEBORDER01(ycfg)
    else:
        weborder = WEBORDER02(ycfg)

    weborder.login_fn()
    Number = weborder.get_ordernum(
        '2018-06-19 10:33:16',
        '2018-06-19 10:39:16')
#     Number = weborder.get_ordernum(
#         '2018-06-19 02:57:09',
#         '2018-06-19 03:03:09')
    # 20180619 02:57:09 20180619 03:03:09

    print 'ordernum=', Number
    print 'JPSS-1+VIIRS'
