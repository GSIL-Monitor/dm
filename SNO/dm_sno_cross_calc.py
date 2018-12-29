# -*- coding: utf-8 -*-
from datetime import datetime
import os
import sys

from configobj import ConfigObj
from dateutil.relativedelta import relativedelta

from PB import pb_time
from PB.CSC.pb_csc_console import LogServer
from dm_sno_cross_calc_core import Sat_Orbit, runSatPassingArea, runSatPassingFixedPoint
from dm_sno_cross_calc_core import runLEO_LEO, runGEO_LEO


__description__ = u'交叉预报'
__author__ = '弢@kingtansin'
__date__ = '2015年10月13日'
__version__ = '1.0.0_beat'

# wangpeng modify 2018-11-26  修改固定点预报，去掉黑白的限制，改为全量预报


def satType(satName):
    GEO_LIST = inCfg['SAT_TYPE']['GEO']
    if satName in GEO_LIST:
        return 'GEO'
    return 'LEO'


def run(sateName, ymd):
    '''
    计算一天的过境时间
    '''
    ORBIT_DIR = inCfg['PATH']['ORBIT']
    CROSS_DIR = inCfg['PATH']['CROSS']

    CROSS_INFO_DICT = inCfg['CROSS']
    AREA_DICT = inCfg['AREA_LIST']
    FIX_DICT = inCfg['FIX_LIST']  # 站点区域配置
    if not os.path.isdir(CROSS_DIR):
        os.makedirs(CROSS_DIR)

    crossInfo = CROSS_INFO_DICT[satName]
    # 轨迹类实例
    s1 = Sat_Orbit(satName, ymd, ORBIT_DIR, Log)
    if s1.error:
        return  # 如果不存在该卫星的目录则返回

    # 过区域
    if 'area_list' in crossInfo.keys() and len(crossInfo['area_list']) > 0:
        if crossInfo['area_list'][0] == 'ALL':
            crossInfo['area_list'] = AREA_DICT.keys()
        sat_over_area(s1, crossInfo['area_list'])

    # 过固定点
    if 'fix_list' in crossInfo.keys() and len(crossInfo['fix_list']) > 0:
        if crossInfo['fix_list'][0] == 'ALL':
            crossInfo['fix_list'] = FIX_DICT.keys()

        if 'fix_dist' in crossInfo.keys():
            fix_dist = float(crossInfo['fix_dist'])
        else:
            fix_dist = 800.  # KM, 缺省距离阈值
        sat_over_fixedpoint(s1, crossInfo['fix_list'], fix_dist)

    # sat cross sat
    if 'sat_list' in crossInfo.keys() and len(crossInfo['sat_list']) > 0:

        if 'sat_dist' in crossInfo.keys():
            sat_dist = float(crossInfo['sat_dist'])
        else:
            return
        if 'sat_time_high' in crossInfo.keys():
            sat_time_high = [float(e) for e in crossInfo['sat_time_high']]
        else:
            sat_time_high = None
        if 'sat_time_low' in crossInfo.keys():
            sat_time_low = [float(e) for e in crossInfo['sat_time_low']]
        else:
            sat_time_low = None

        sat_over_sat(
            s1, crossInfo['sat_list'], sat_dist, sat_time_high, sat_time_low)


def sat_over_area(s1, area_list):
    '''
    计算一天的过境时间
    '''
    CROSS_DIR = inCfg['PATH']['CROSS']
    AREA_DICT = inCfg['AREA_LIST']
    for eachArea in area_list:
        Log.info('[%-12s] [%-8s] [%-8s]' % (s1.sat, eachArea, s1.ymd))
        crossFile = os.path.join(CROSS_DIR, '%s_%s' % (
            s1.sat, eachArea), '%s_%s_%s.txt' % (s1.sat, eachArea, s1.ymd))
#         # 预报文件存在则跳过
#         if os.path.isfile(crossFile):
#             Log.info('already exists')
#             continue
        latlonInfo = AREA_DICT[eachArea]
        runSatPassingArea(s1, eachArea, latlonInfo, crossFile, Log)


def sat_over_fixedpoint(s1, fix_list, fix_dist):
    '''
    计算两天的过固定点时间
    '''
    CROSS_DIR = inCfg['PATH']['CROSS']
    FIX_DICT = inCfg['FIX_LIST']
    Log.info('[%-12s] [FIX] [%-8s]' % (s1.sat, s1.ymd))
    crossFile = os.path.join(
        CROSS_DIR, '%s_FIX' % s1.sat, '%s_FIX_%s.txt' % (s1.sat, s1.ymd))
    # 预报文件存在则跳过
#     if os.path.isfile(crossFile):
#         Log.info('already exists')
#         return

    runSatPassingFixedPoint(s1, fix_list, fix_dist, crossFile, FIX_DICT, Log)


def sat_over_sat(s1, sat_list, sat_dist, sat_time_high, sat_time_low):
    '''
    星星交叉
    s1: Sat_Orbit类对象
    sat_list: 目标卫星名列表
    sat_dist: 距离阈值
    sat_time_high： 高纬时间阈值
    sat_time_low：低纬时间阈值
    '''
    ORBIT_DIR = inCfg['PATH']['ORBIT']
    CROSS_DIR = inCfg['PATH']['CROSS']

    i = -1
    for eachSat in sat_list:
        Log.info('[%-12s] [%-12s] [%-8s]' % (s1.sat, eachSat, s1.ymd))
        i = i + 1
#         crossFile = os.path.join(CROSS_DIR, '%s_%s' % (eachSat, s1.sat), '%s_%s_%s.txt' % (eachSat, s1.sat, s1.ymd))
#         # 预报文件存在则跳过
#         if os.path.isfile(crossFile):
#             Log.info('already exists')
#             continue
        crossFile = os.path.join(CROSS_DIR, '%s_%s' % (
            s1.sat, eachSat), '%s_%s_%s.txt' % (s1.sat, eachSat, s1.ymd))
#         # 预报文件存在则跳过
#         if os.path.isfile(crossFile):
#             Log.info('already exists')
#             continue

        if satType(s1.sat) == 'LEO' and satType(eachSat) == 'LEO':
            if sat_time_high is None:
                continue
            if sat_time_low is None:
                continue
            if len(sat_time_high) == len(sat_time_low) == len(sat_list):
                s2 = Sat_Orbit(eachSat, s1.ymd, ORBIT_DIR, Log)
                if s2.error:
                    Log.error('No Orbit File of %s' % eachSat)
                    continue
                runLEO_LEO(
                    s1, s2, sat_dist, sat_time_high[i], sat_time_low[i], crossFile, Log)
            else:
                Log.error(
                    "%s : the Length of sat_time_low, sat_time_high and sat_list are not the same!" % s1.sat)
        elif satType(s1.sat) == 'GEO' and satType(eachSat) == 'LEO':
            s2 = Sat_Orbit(eachSat, s1.ymd, ORBIT_DIR, Log)
            if s2.error:
                continue
            runGEO_LEO(s2, s1, sat_dist, crossFile, Log)

        elif satType(s1.sat) == 'LEO' and satType(eachSat) == 'GEO':
            s2 = Sat_Orbit(eachSat, s1.ymd, ORBIT_DIR, Log)
            if s2.error:
                continue
            runGEO_LEO(s1, s2, sat_dist, crossFile, Log)

# 程序全局入口

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

# 手动执行跟2个参数，卫星明和时间段
if len(args) == 2:
    Log.info(u'手动交叉预报程序开始运行-----------------------------')

    satName = args[0]  # 卫星全名
    str_time = args[1]  # 程序执行时间范围
    date_s, date_e = pb_time.arg_str2date(str_time)
    while date_s <= date_e:
        ymd = date_s.strftime('%Y%m%d')
        run(satName, ymd)
        date_s = date_s + relativedelta(days=1)

# 自动执行不跟参数，卫星明和时间段从配置中获取
elif len(args) == 0:
    Log.info(u'自动交叉预报程序开始运行-----------------------------')

    CROSS_DAYS = inCfg['CROSS']['CROSS_DAYS']
    rolldays = inCfg['CROND']['rolldays']
    satLst = inCfg['CROSS'].keys()
    satLst.pop(0)

    if int(CROSS_DAYS) <= 0:
        CROSS_DAYS = 1

    # 滚动日期的第一个日期需要向后计算N天（CROSS_DAYS），制作时间段
    rdays = rolldays[0]
    date_s = datetime.utcnow() - relativedelta(days=int(rdays))
    date_e = date_s + relativedelta(days=int(CROSS_DAYS))
    # 剔除第一个日期滚动日期阈值
    rolldays.pop(0)

    # 开始按照时间处理所有卫星的预报
    while date_s <= date_e:
        ymd = date_s.strftime('%Y%m%d')
        for satName in satLst:
            run(satName, ymd)
        date_s = date_s + relativedelta(days=1)
    # 开始滚动其余时间的所有卫星的预报计算
    for satName in satLst:
        for rdays in rolldays:
            ymd = (
                datetime.utcnow() - relativedelta(days=int(rdays))).strftime('%Y%m%d')
            run(satName, ymd)
else:
    print 'args: satName yyyymmdd-yyyymmdd'
    sys.exit(-1)
