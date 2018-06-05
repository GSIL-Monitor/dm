# coding=UTF-8
__author__ = 'wangpeng'

'''
FileName:     sno_orbit_cal.py
Description:  卫星轨迹计算
Author:       wangpeng
Date:         2015-06-13
version:      1.0.0.050613_beat
Input:        args1:开始时间  args2:结束时间  [YYYYMMDD-YYYYMMDD]
Output:       (^_^)
'''

import os, sys
from datetime import datetime
from dateutil.relativedelta import relativedelta
from configobj import ConfigObj
from posixpath import join as urljoin
from PB import pb_time
from PB.CSC.pb_csc_console import LogServer

def run(satName, ymd):
    '''
    卫星名称和字符时间
    '''
    # 解析配置文件KEY
    TITLE_DIR = inCfg['PATH']['TITLE']
    ORBIT_DIR = inCfg['PATH']['ORBIT']
    ORBIT_EXE = inCfg['ORBIT']['ORBIT_EXE']

    if 'nt' in os.name:
        OSTYPE = 'windows'
        trash = 'nul'
    elif 'posix' in os.name:
        OSTYPE = 'linux'
        trash = '/dev/null'
    else:
        Log.error('不识别的系统类型')
        sys.exit(-1)
    # 需要调用第三方exe来进行轨迹计算
    FULL_ORBIT_EXE = urljoin(ProjPath, 'BIN', OSTYPE, ORBIT_EXE)

    if not os.path.isfile(FULL_ORBIT_EXE):
        Log.error(u'Not Found %s' % FULL_ORBIT_EXE)
        return
    strYmd = ymd + '000000'
    FULL_ORBIT_DIR = urljoin(ORBIT_DIR, satName)
    FULL_TITLE_DIR = urljoin(TITLE_DIR, satName)
    ORBIT_FILE = urljoin(FULL_ORBIT_DIR, ymd + '.txt')

    # 轨迹文件存在则跳过

    if os.path.isfile(ORBIT_FILE):
        fileSize = os.path.getsize(ORBIT_FILE)
        if fileSize >= 3974562:
            Log.info(u'轨迹文件已经存在 [%s] [%s]' % (ymd, satName))
            return

    if not os.path.exists(FULL_ORBIT_DIR):
        os.makedirs(FULL_ORBIT_DIR)

    # 执行轨迹计算可执行程序
    cmd = '%s %s %s %s %s %s > %s ' % (FULL_ORBIT_EXE, satName, FULL_TITLE_DIR, strYmd, strYmd, ORBIT_FILE, trash)
    os.system(cmd)

    if os.path.isfile(ORBIT_FILE):
        fileSize = os.path.getsize(ORBIT_FILE)
        # linux下一天的轨迹大小byte
        if fileSize >= 390000:
            Log.info(u'轨迹计算 [%s] [%s] 成功 ' % (ymd, satName))
        else:
            Log.error(u'轨迹计算 [%s] [%s] 失败 ' % (ymd, satName))
            os.unlink(ORBIT_FILE)
    return

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

# 获取程序所在位置，拼接配置文件
MainPath, MainFile = os.path.split(os.path.realpath(__file__))
ProjPath = os.path.dirname(MainPath)
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
    satName = args[0]  # 卫星全名
    str_time = args[1]  # 程序执行时间范围

    date_s, date_e = pb_time.arg_str2date(str_time)
    Log.info(u'手动轨迹计算程序开始运行-----------------------------')
    while date_s <= date_e:
        ymd = date_s.strftime('%Y%m%d')
        run(satName, ymd)
        date_s = date_s + relativedelta(days=1)

# 自动执行不跟参数，卫星明和时间段从配置中获取
elif len(args) == 0:
    Log.info(u'自动轨迹计算程序开始运行-----------------------------')
    ORBIT_DAYS = inCfg['ORBIT']['ORBIT_DAYS']
    rolldays = inCfg['CROND']['rolldays']
    satLst = inCfg['SAT_ID'].keys()

    if int(ORBIT_DAYS) <= 0:
        ORBIT_DAYS = 1

    # 滚动日期的第一个日期需要向后计算N天（ORBIT_DAYS），制作时间段
    rdays = rolldays[0]
    date_s = datetime.utcnow() - relativedelta(days=int(rdays))
    date_e = date_s + relativedelta(days=int(ORBIT_DAYS))
    # 剔除第一个日期滚动日期阈值
    rolldays.pop(0)

    # 开始按照时间处理所有卫星的轨迹计算
    while date_s <= date_e:
        ymd = date_s.strftime('%Y%m%d')
        for satName in satLst:
            run(satName, ymd)
        date_s = date_s + relativedelta(days=1)
    # 开始滚动其余时间的所有卫星轨迹计算
    for satName in satLst:
        for rdays in rolldays:
            ymd = (datetime.utcnow() - relativedelta(days=int(rdays))).strftime('%Y%m%d')
            run(satName, ymd)
else:
    print 'args: satName yyyymmdd-yyyymmdd or args: NULL'
    sys.exit(-1)
