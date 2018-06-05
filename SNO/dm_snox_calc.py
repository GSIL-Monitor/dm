# coding:UTF-8
'''
Created on 2017年07月13日

@author: 弢@kingtansin
'''
import sys, os
from dateutil.relativedelta import relativedelta
from configobj import ConfigObj
# from dm_sno_cross_calc_core import Sat_Orbit, runLEO_LEO_SNOX
from dm_sno_cross_calc_core_snox import Sat_Orbit, runLEO_LEO_SNOX
from PB import pb_time
from PB.CSC.pb_csc_console import LogServer

def satType(satName):
    GEO_LIST = OdmCfg['SAT_TYPE']['GEO']
    if satName in GEO_LIST: return 'GEO'
    return 'LEO'

def run(date_s, date_e):
    '''
    计算SNOX时间
    '''
    OUT_ROOT = OdmCfg['PATH']['CROSS']
    ORBIT_ROOT = OdmCfg['PATH']['ORBIT']
    CROSS_INFO_DICT = OdmCfg['SNOX']
    if not os.path.isdir(OUT_ROOT):
        os.makedirs(OUT_ROOT)

    while date_s <= date_e:
        ymd = date_s.strftime('%Y%m%d')
        for satName in CROSS_INFO_DICT:
            crossInfo = CROSS_INFO_DICT[satName]
            # 轨迹类实例
            s1 = Sat_Orbit(satName, ymd, ORBIT_ROOT, Log)
            if s1.error: continue  # 如果不存在该卫星的目录则返回

            # sat cross sat
            # if 'sat_list' in crossInfo.keys() and len(crossInfo['sat_list']) > 0:
            if 'sat_list' in crossInfo.keys() and len(crossInfo['sat_list']) > 0:
                if 'sat_dist' in crossInfo.keys():
                   # sat_dist = float(crossInfo['sat_dist'])
                    sat_dist = crossInfo['sat_dist']
                else:
                    continue
                if 'sat_time' in crossInfo.keys():
                    sat_time = [float(e) for e in crossInfo['sat_time']]
                else:
                    sat_time = None

                sat_near_sat(s1, crossInfo['sat_list'], sat_dist, sat_time)

        date_s = date_s + relativedelta(days=1)


def sat_near_sat(s1, sat_list, sat_dist, sat_time):
    '''
    星、星在赤道附近近平行
    s1: Sat_Orbit类对象
    sat_list: 目标卫星名列表
    sat_dist: 距离阈值
    sat_time： 时间阈值
    '''
    OUT_ROOT = OdmCfg['PATH']['SNOX']
    ORBIT_ROOT = OdmCfg['PATH']['ORBIT']

    i = -1
    for eachSat in sat_list:
        Log.info('[%-12s] [%-12s] [%-8s]' % (s1.sat, eachSat, s1.ymd))
        i = i + 1
#         crossFile = os.path.join(OUT_ROOT, '%s_%s' % (eachSat, s1.sat), '%s_%s_%s.txt' % (eachSat, s1.sat, s1.ymd))
#         # 预报文件存在则跳过
#         if os.path.isfile(crossFile):
#             Log.info('already exists')
#             continue
        snoxFile = os.path.join(OUT_ROOT, '%s_%s' % (s1.sat, eachSat), '%s_%s_SNOX_%s.txt' % (s1.sat, eachSat, s1.ymd))
#         # 预报文件存在则跳过
#         if os.path.isfile(crossFile):
#             Log.info('already exists')
#             continue

        if satType(s1.sat) == 'LEO' and satType(eachSat) == 'LEO':
            if sat_time is None: continue
            if len(sat_time) == len(sat_list):
                s2 = Sat_Orbit(eachSat, s1.ymd, ORBIT_ROOT, Log)
                if s2.error:
                    Log.error('No Orbit File of %s' % eachSat)
                    continue
                runLEO_LEO_SNOX(s1, s2, float(sat_dist[i]), sat_time[i], snoxFile, Log)
            else:
                Log.error("%s : the Length of sat_time and sat_list are not the same!" % s1.sat)


'''
    input: 配置文件的路径，时间段
'''
args = sys.argv[1:]
if len(args) == 2:
        str_conf = args[0]
        str_time = args[1]
        if not os.path.isfile(str_conf):
            print (u'配置文件不存在 %s' % str_conf)
            sys.exit(-1)
        OdmCfg = ConfigObj(str_conf)
        day_counts = int(OdmCfg['ORBIT']['ORBIT_DAYS'])  # 轨迹算几天，预报算几天
        date_s, date_e = pb_time.arg_str2date(str_time)
        date_e = date_e + relativedelta(days=(day_counts - 1))

else:  # 跟参数，则处理输入的时段数据
    print 'args: cfgFile yyyymmdd-yyyymmdd'
    sys.exit(-1)

LogPath = OdmCfg['PATH']['LOG']
Log = LogServer(LogPath)
Log.info(u'交叉点预报程序开始运行-----------------------------')

run(date_s, date_e)

