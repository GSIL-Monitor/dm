# coding: utf-8
__author__ = 'wangpeng'

'''
FileName:     dm_sno_title_down.py
Description:  下载卫星轨道报文
Author:       wangpeng
Date:         2015-08-13
version:      1.0.0.050813_beat
Input:        args1:开始时间  args2:结束时间  [YYYYMMDD-YYYYMMDD]
Output:       (^_^)
'''
import os, sys, time, random
import urllib, urllib2
from HTMLParser import HTMLParser
from posixpath import join as urljoin
from configobj import ConfigObj
from datetime import datetime
from dateutil.relativedelta import relativedelta
import socket
from PB import pb_time
from PB.CSC.pb_csc_console import LogServer

# 设置访问html超时时间
# socket.setdefaulttimeout(60)

def run(satName, ymd):
    '''
    批量下载卫星报文，调度功能 内部接口走datetime格式，外部接口走main
    :param date_s:
    :param date_e:
    :return:
    '''
    # 读取配置文件
    URL = inCfg['TITLE']['URL']
    DELAY = inCfg['TITLE']['DELAY']
    TITLE_DIR = inCfg['PATH']['TITLE']
    date_s = datetime.strptime(ymd, '%Y%m%d')

    satid = inCfg['SAT_ID'][satName]
    TITLE_FILE = urljoin(TITLE_DIR, satName, ymd + '.txt')
    # 报文文件存在则跳过
    if os.path.isfile(TITLE_FILE):
        Log.info(u'报文已经存在 [%s] [%s]' % (ymd, satName))
        return
    # 计算当前日期距离公元1年1月1日的天数，在加上 1 + 1721425.5 天 就是网站上的表达日期的方式。
    tdt = (date_s - datetime(0001, 1, 1, 0, 0, 0)).total_seconds() / 3600. / 24. + 1 + 1721425.5
    url = URL % (satid, tdt)
    # 获取url页面
    # print '%-12s %-8s title start' % (sat, ymd)
    time.sleep(int(random.uniform(1, 10)))  # 获取随机数
    the_page = getHtml(url)  # 连接网页进行页面的下载
    if the_page is None:
        Log.error(u'获取html页面信息失败 [%s] [%s]' % (ymd, satName))
        return

    # 类的实例化, 获取报文内容和更新时间
    anaHtml = AnaHtml()
    anaHtml.feed(the_page)
    anaHtml.close()
    TD, tle_message = anaHtml.getStr()
    td = float(TD)
    delay = int(DELAY)
    # 判断报文是否更新，是当天则更新
    if date_is_update(td, date_s, delay):
        Log.info(u'下载 [%s] [%s] 成功 ' % (ymd, satName))
        tle_write(TITLE_FILE, satName, tle_message)
    else:
        Log.error(u'下载 [%s] [%s] 失败 ' % (ymd, satName))
        # print '%-12s %-8s down title failed' % (sat, ymd)

def getHtml(url):
    '''
    连接URL 并返回页面内容
    :param url:
    :return:
    '''
    user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows XP)'
    values = {'name': 'Michael Foord',
              'location': 'Northampton',
              'language': 'Python'}
    headers = {'User-Agent': user_agent}
    data = urllib.urlencode(values)  # 将URL中的键值对以连接符&划分
    try:
        requ = urllib2.Request(url, data, headers)
        response = urllib2.urlopen(requ)
    except Exception, e:
        print str(e)
        return None
    the_page = response.read()
    response.close()
    return the_page


class AnaHtml(HTMLParser):
    '''
    网页解析，获取想要的时间和两行报
    '''
    def __init__(self):
        self.tle_message = []
        self.tle_date = []
        self.pre = False
        self.b = False
        self.jd = False
        HTMLParser.__init__(self)

    def handle_starttag(self, tag, attrs):
        if tag == 'pre':
            self.pre = True
        if tag == 'b':
            self.b = True


    def handle_endtag(self, tag):
        if tag == 'pre':
            self.pre = False
        if tag == 'b':
            self.b = False

    def handle_data(self, data):

        if not self.b:
            if 'JD=' in data:
                self.tle_date = data.strip().split('=')[1][0:-1]
                self.pre = False
                self.jd = True
        if self.pre and self.b and self.jd:
            tl1 = data.strip().split('\n')[1] + '\n'
            tl2 = data.strip().split('\n')[2] + '\n'
            self.tle_message.append(tl1)
            self.tle_message.append(tl2)

    def getStr(self):
        return self.tle_date, self.tle_message


def tle_write(o_file, sat, tle_message):
    '''
    写入报文  卫星名+两行报
    :param date_s:
    :param sat:
    :param tle_message:
    :return:
    '''
    o_dir = os.path.dirname(o_file)
    if not os.path.isdir(o_dir):
        os.makedirs(o_dir)
    fp = open(o_file, 'w')
    fp.write('%s\n' % sat)
    fp.writelines(tle_message)
    fp.close()


def date_is_update(td, date_s, delay):
    '''
    判断页面时间和要获取的报文时间是否一致
    :param td:
    :param date_s:
    :return:
    '''
    seconds = (td - 1721425.5) * 24 * 3600
    page_date = datetime(0001, 1, 1, 0, 0, 0) + relativedelta(seconds=seconds)
    # print page_date.strftime('%Y%m%d') , date_s.strftime('%Y%m%d')
    ymd1 = date_s.strftime('%Y%m%d')
    ymd2 = page_date.strftime('%Y%m%d')
    date1 = datetime.strptime(ymd1, '%Y%m%d')
    date2 = datetime.strptime(ymd2, '%Y%m%d')
    # print date_s, page_date
    diff_day = (date1 - date2).days
    if diff_day <= delay:
        return True
    else:
        return False



######################### 程序全局入口 ##############################
# 获取命令行参数
args = sys.argv[1:]

help_info = \
    u'''
        【参数1】：卫星全名
        【参数2】：yyyymmdd-yyyymmdd
    '''
if '-h' in args:
    print help_info
    sys.exit(-1)

# 设置超时时间
socket.setdefaulttimeout(60)

# 获取程序所在位置，拼接配置文件
MainPath, MainFile = os.path.split(os.path.realpath(__file__))
# cfgName = MainFile.split('.')[0]
cfgFile = os.path.join(MainPath, 'dm_sno.cfg')
# 配置不存在预警
if not os.path.isfile(cfgFile):
    print (u'配置文件不存在 %s' % cfgFile)
    sys.exit(-1)
# 载入配置文件
inCfg = ConfigObj(cfgFile)
LogPath = inCfg['PATH']['LOG']  # log存放地址
Log = LogServer(LogPath)

# 手动执行跟2个参数，卫星明和时间段
if len(args) == 2:
    Log.info(u'手动报文下载程序开始运行-----------------------------')
    # 解析参数
    satName = args[0]  # 卫星全名
    str_time = args[1]  # 程序执行时间范围
    date_s, date_e = pb_time.arg_str2date(str_time)

    while date_s <= date_e:
        ymd = date_s.strftime('%Y%m%d')
        run(satName, ymd)
        date_s = date_s + relativedelta(days=1)

# 自动执行不跟参数，卫星明和时间段从配置中获取
elif len(args) == 0:
    Log.info(u'自动报文下载程序开始运行-----------------------------')

    rolldays = inCfg['CROND']['rolldays']
    satLst = inCfg['SAT_ID'].keys()
    for satName in satLst:
        for rdays in rolldays:
            ymd = (datetime.utcnow() - relativedelta(days=int(rdays))).strftime('%Y%m%d')
            run(satName, ymd)
else:
    print 'args: satName yyyymmdd-yyyymmdd or args: NULL'
    sys.exit(-1)


