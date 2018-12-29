# -*- coding: utf-8 -*-

from HTMLParser import HTMLParser
from StringIO import StringIO
from datetime import datetime
import csv
import ftplib
import os
import random
import re
import socket
import subprocess
import sys
import time
import urllib
import urllib2

from configobj import ConfigObj
from dateutil.relativedelta import relativedelta
import ftputil
import paramiko
import socks
import threadpool

from PB import pb_time, pb_sat, pb_name
from PB.CSC.pb_csc_console import LogServer, SocketServer, MailServer_imap
from dm_odm_order_core import WEBORDER01, WEBORDER02, ReadYaml


# from posixpath import join as urljoin
socket.setdefaulttimeout(120)  # 设置访问socket连接超时时间

__description__ = u'订购模块'
__author__ = 'wangpeng'
__date__ = '2018-05-30'
__version__ = '1.0.0_beat'
__updated__ = '2018-07-09'


def run(satID, ymd):
    # 获取每个卫星，传感器的参数
    webOrder = inCfg['ORDER'][satID]['WEB_ORDER']
    areaList = inCfg['ORDER'][satID]['TARGET_AREA']
    # 判断订购的方式，‘YES’表示通过web进行订购，‘GOLBAL’表示订购全部，其他的表示根据限定条件进行订购
    if 'YES' in webOrder:
        OrderWebProduct(satID, ymd)
    else:
        if 'GLOBAL' in areaList:
            OrderGlobalProduct(satID, ymd)
        else:
            OrderOrbitProduct(satID, ymd)


def OrderWebProduct(satID, ymd):
    # 获取每个卫星，传感器的参数
    sat = inCfg['ORDER'][satID]['SELF_SAT']
    sensor = inCfg['ORDER'][satID]['SELF_SENSOR']
    product = inCfg['ORDER'][satID]['SELF_PRODUCT']
    interval = inCfg['ORDER'][satID]['SELF_INTERVAL']

#     javaName = inCfg['TOOL']['java']
#     # 20160822 huangyj
#     # 拼接DM/BIN/ 下面的jar包应用程序
#     JarName = inCfg['TOOL']['jar']
#     # MainPath = os.path.dirname(os.getcwd())
#     FullJarName = os.path.join(ProjPath, 'BIN', OSTYPE, JarName)

    regList = inCfg['ORDER'][satID]['SELF_REG']
    surl = inCfg['ORDER'][satID]['HOST']
    pact = surl.split('://')[0]
    port = inCfg['ORDER'][satID]['PORT']
#     pact = 'ftp'
#     port = '21'
    # 判断jar包是否存在（路径是否正确）
#     if not os.path.isfile(FullJarName):
#         Log.error(u'---- web订购需要的jar程序未找到 [%s]' % FullJarName)
#         return

    timeList = []  # 解析预报文件获取时间

    # 根据交叉点文件获取时间段（CAPIPSO除外）
    if 'CALIPSO' in sat:
        stime = datetime.strptime(ymd, '%Y%m%d')
        etime = datetime.strptime(ymd, '%Y%m%d')
        timeList.append([stime, etime])

    else:
        sat_areaList = ReadForecastFile_area(satID, ymd)  # 区域预报
        timeList.extend(sat_areaList)
        sat_fixList = ReadForecastFile_fix(satID, ymd)  # 固定点预报
        timeList.extend(sat_fixList)
        sat_satList = ReadForecastFile_sat(satID, ymd)  # 卫星-卫星预报
        timeList.extend(sat_satList)

    # 将重叠部分时间进行扩展形成新的时间段（在JAVA订购方式时会需要，避免重复订购）
    if len(timeList) != 0:
        combine_timeList = CombineTimeList(timeList)
    else:
        # Log.error(u'----没有有效的交叉点时间')
        Log.error(u'---- WEB订购  [%s] [%s] %s %s %s %s 没有有效的交叉点时间' %
                  (ymd, satID, sat, sensor, product, interval))
        return

#     allServerList = []  # 获取FTP清单文件
    allorderList = []  # 记录订单文件
    dict_Flst = {}
    # 创建轨道产品订单文件
    orderFile = os.path.join(ORDER_DIR, satID, ymd + '.txt')
    ycfg = ReadYaml(sat, sensor)
    if ycfg.init_type == '1':
        weborder = WEBORDER01(ycfg)
    else:
        weborder = WEBORDER02(ycfg)
    weborder.login_fn()
    for ctime in combine_timeList:
        time_range = ctime[0].strftime(
            '%Y%m%d%H%M%S') + '_' + ctime[1].strftime('%Y%m%d%H%M%S')
        stime = ctime[0].strftime('%Y%m%d %H:%M:%S')
        etime = ctime[1].strftime('%Y%m%d %H:%M:%S')
        o_stime = ctime[0].strftime('%Y-%m-%d %H:%M:%S')
        o_etime = ctime[1].strftime('%Y-%m-%d %H:%M:%S')
        FULL_ID_DIR = os.path.join(ID_DIR, satID, ymd, time_range)
        # 检查java订购ID是否有效
        ID = CheckIdAvailable(FULL_ID_DIR)
        if ID is None:  # id号不可用则重新订购
            time.sleep(int(random.uniform(1, 10)))
            try:

                ID = weborder.get_ordernum(o_stime, o_etime)

            except:
                ID = None

            # 判断ID号是否符合标准
            if is_num_by_except(ID):
                mailFile = os.path.join(FULL_ID_DIR, ID + '.eml')
                # print 'mailFile    :', mailFile
                WriteOrderNumber(mailFile)
                Log.info(u'---- WEB订购  [%s] [%s] %s %s %s %s 时段: [%s] ID: [%s] 下单成功' %
                         (ymd, satID, sat, sensor, product, interval, time_range, ID))
            else:
                Log.error(u'---- WEB订购  [%s] [%s] %s %s %s %s 时段: [%s] ID: [%s] 下单失败' % (
                    ymd, satID, sat, sensor, product, interval, time_range, ID))
                continue
        else:  # 如果已经订购过，则直接处理
            # Log.info(u'----时段: [%s] ID: [%s] ID号可用' % (time_range, ID))
            mailFile = os.path.join(FULL_ID_DIR, ID + '.eml')
            # print 'FULL_ID_DIR is :', FULL_ID_DIR
            # print  'mailFile is :',mailFile
            if os.path.isfile(mailFile) and os.path.getsize(mailFile) > 0:
                Log.info(u'---- WEB订购  [%s] [%s] %s %s %s %s 时段: [%s] ID: [%s] ID号可用' %
                         (ymd, satID, sat, sensor, product, interval, time_range, ID))
                f_host, f_user, f_pawd, f_path = getftpinfo(mailFile)
                time.sleep(int(random.uniform(1, 10)))
                try:
                    serverList = GetServerList(
                        pact, f_host, sensor, f_user, f_pawd, port, f_path, regList, ymd)
                except Exception as e:
                    print str(e)
                    continue

                # 由于国外数据（NPP等）文件名内函数随机数，造成数据重复下载获取或者同时下载造成数据错误
                # 以'-'分割提取数据文件名的前5个字符串，并以'-'为分隔符组成新的字符串作为字典的Key值。确保一天的订单内不会有重复的数据
                for each in serverList:
                    fileName = each.split()[0]
                    fileSize = each.split()[1]
                    KeyWorld = '_'.join(fileName.split('_')[0:5])
                    if KeyWorld not in dict_Flst.keys():
                        dict_Flst[KeyWorld] = [
                            fileName, fileSize, f_host, f_path]
#                 newServerLst = dict_Flst.values()
#
#
#                 # 把每个时次的ftp目录下的文件保存
#                 if len(newServerLst) != 0:
#                     allServerList.extend(newServerLst)
#                     for info in newServerLst:
#                         FileName = info.split()[0].strip()
#                         url = pact + '://' + f_host + ':' + port + f_path + '/' + FileName + '\n'
#                         allorderList.append(url)
            else:  # 邮件没有下载到本地
                try:
                    time.sleep(int(random.uniform(1, 10)))
                    m = MailServer_imap(MAIL_HOST, ID)
                    m.connect(MAIL_USER, MAIL_PAWD)
                    m.findspam()  # 垃圾邮箱无用信息，直接删掉
                    if (m.findmail()):
                        # Log.info(u'----时段: [%s] ID: [%s] 邮件已到' % (time_range, ID))
                        m.savemail(mailFile)
                        Log.error(u'---- WEB订购  [%s] [%s] %s %s %s %s 时段: [%s] ID: [%s] 保存邮件' % (
                            ymd, satID, sat, sensor, product, interval, time_range, ID))
                        # u'delete 订购邮件'
                    else:
                        # Log.info(u'----时段: [%s] ID: [%s] 邮件未到' % (time_range, ID))
                        Log.error(u'---- WEB订购  [%s] [%s] %s %s %s %s 时段: [%s] ID: [%s] 邮件未到' % (
                            ymd, satID, sat, sensor, product, interval, time_range, ID))
                    m.close()
                    m.logout()
                except Exception as e:
                    print (u'mail----%s' % str(e))
                    Log.error(u'---- WEB订购  [%s] [%s] %s %s %s %s 时段: [%s] ID: [%s] 获取邮件信息超时' % (
                        ymd, satID, sat, sensor, product, interval, time_range, ID))

    # 将写入字典的文件进行信息提取，形成订单列表和订单信息列表
    F_serverList = []
    for serverList in dict_Flst.values():
        filename = serverList[0]
        filesize = serverList[1]
        file_host = serverList[2]
        file_path = serverList[3]
        F_serverList.append(filename + "   " + filesize + '\n')
        url = pact + '://' + file_host + ':' + \
            port + file_path + '/' + filename + '\n'
        allorderList.append(url)

    # 写入订单信息文件
    if len(F_serverList) != 0:
        infoFile = os.path.join(ORDER_DIR, satID, ymd + '.info')
        WriteFile(infoFile, F_serverList)
    else:
        Log.error(u'---- WEB订购  [%s] [%s] %s %s %s %s FTP清单获取失败' %
                  (ymd, satID, sat, sensor, product, interval))
        return
    # 写入订单文件
    if len(allorderList) != 0:
        Log.info(u'---- WEB订购  [%s] [%s] %s %s %s %s 订购成功' %
                 (ymd, satID, sat, sensor, product, interval))
        WriteFile(orderFile, allorderList)
    else:
        Log.error(u'---- WEB订购  [%s] [%s] %s %s %s %s 订购失败' %
                  (ymd, satID, sat, sensor, product, interval))


def getftpinfo(mailFile):
    # 从邮件文件中获取服务器的登录信息
    f_host = []
    f_user = []
    f_pawd = []
    f_path = []

    ordernum = os.path.basename(mailFile).split('.')[0]
    if os.path.isfile(mailFile):
        fp = open(mailFile, 'r')
        Lines = fp.readlines()
        fp.close()
        for line in Lines:
            if 'hostname:' in line:
                f_host = line.split()[1].strip()
            elif '- Logon to CLASS system' in line:
                f_host = line.split()[1].strip()
            if 'login:' in line:
                f_user = line.split()[1].strip()
            elif ' - FTP user id' in line:
                f_user = line.split()[0].strip()
            if 'password:' in line:
                f_pawd = line.split()[1].strip()
                f_pawd = f_pawd.replace('(', '')
                f_pawd = f_pawd.replace(')', '')
            elif '- FTP password' in line:
                f_pawd = line.split()[0].strip()
            if len(line.strip()) == 24:
                if 'cd' in line and ordernum in line:
                    f_path = '/' + line.split()[1].strip()
            elif 'cd' in line and ordernum in line and 'get' in line:
                f_path = '/' + line.split()[1].strip() + '/001'
            elif 'cd' in line and ordernum in line:
                f_path = '/' + line.split()[1].strip() + '/001'
    return f_host, f_user, f_pawd, f_path


def WriteOrderNumber(MailFile):
    '''
    把订单号保存到本地
    '''
    if not os.path.isdir(os.path.dirname(MailFile)):
        os.makedirs(os.path.dirname(MailFile))
    if not os.path.isfile(MailFile):
        fp = open(MailFile, 'w')
        fp.close()


def is_num_by_except(satID):
    '''
    检查订单号是否合法
    '''
    if satID is None:
        return False
    try:
        if int(satID) > 0:
            return True
    except ValueError:
        return False


def CheckIdAvailable(ID_DIR):
    '''
    检测每个交点上的时段订单号是否可用
    '''
    sysTime = datetime.now()
    fileList = []
    if os.path.isdir(ID_DIR):
        Lst = sorted(os.listdir(ID_DIR), reverse=False)
        for mailFile in Lst:
            FullPath = os.path.join(ID_DIR, mailFile)
            if os.path.isfile(FullPath):
                # 输出文件创建时间
                timestamp = os.path.getctime(FullPath)
                # 根据给定的时间戮，返回一个date对象
                mailTime = datetime.fromtimestamp(timestamp)
                idnum = mailFile.split('.')[0]
                fileList.append([idnum, mailTime])

    if len(fileList) > 0:
        # 找到最后一次被创建的订单ID，判断在5天内则是有效的。
        fileList = sorted(fileList, key=lambda d: d[1], reverse=True)
        id_nums = fileList[0][0]
        id_time = fileList[0][1]
        # 调度的滚动日期目前最大15天，所有订购过的就不会重复订购，实际数据准备后只有4天有效时间
        if (sysTime - id_time).days <= 15:
            return id_nums
        else:
            return None
    else:
        return None


def OrderOrbitProduct(satID, ymd):
    # 获取每个卫星，传感器的参数
    sat = inCfg['ORDER'][satID]['SELF_SAT']
    sensor = inCfg['ORDER'][satID]['SELF_SENSOR']
    product = inCfg['ORDER'][satID]['SELF_PRODUCT']
    interval = inCfg['ORDER'][satID]['SELF_INTERVAL']

    orderList = []
    surl = inCfg['ORDER'][satID]['HOST']
    pact = surl.split('://')[0]
    host = surl.split('://')[1]
    port = inCfg['ORDER'][satID]['PORT']
    user = inCfg['ORDER'][satID]['USER']
    pawd = inCfg['ORDER'][satID]['PAWD']
    sdir = inCfg['ORDER'][satID]['SDIR']
    SELF_SENSOR = inCfg['ORDER'][satID]['SELF_SENSOR']
    regList = inCfg['ORDER'][satID]['SELF_REG']

    stime = datetime.strptime(ymd, '%Y%m%d')
    jjj = stime.strftime('%j')
    # 替换字符中的%YYYY%MM%DD为当前输入时间
    sdir = sdir.replace('%YYYY', ymd[0:4])
    sdir = sdir.replace('%MM', ymd[4:6])
    sdir = sdir.replace('%DD', ymd[6:8])
    s_path = sdir.replace('%JJJ', jjj)

    # 解析预报文件获取时间
    timeList = []
    # 区域预报
    sat_areaList = ReadForecastFile_area(satID, ymd)
    timeList.extend(sat_areaList)
    # 固定点预报
    sat_fixList = ReadForecastFile_fix(satID, ymd)
    timeList.extend(sat_fixList)
    # 卫星-卫星预报
    sat_satList = ReadForecastFile_sat(satID, ymd)
    timeList.extend(sat_satList)
    # 将重叠部分时间进行扩展形成新的时间段（在JAVA订购方式时会需要，避免重复订购）
    if len(timeList) != 0:
        combine_timeList = CombineTimeList(timeList)
    else:
        #         Log.error(u'----没有有效的交叉点时间')
        Log.error(u'---- 选择订购  [%s] [%s] %s %s %s %s 没有有效的交叉点时间 ' %
                  (ymd, satID, sat, sensor, product, interval))
        return

    time.sleep(int(random.uniform(1, 10)))
    # 获取FTP上的数据信息列表
    serverList = GetServerList(
        pact, host, SELF_SENSOR, user, pawd, port, s_path, regList, ymd)
    F_serverList = [
        each + '\n' for each in serverList if not each.startswith('.')]
    if len(F_serverList) != 0:
        infoFile = os.path.join(ORDER_DIR, satID, ymd + '.info')
        WriteFile(infoFile, F_serverList)
    else:
        #         Log.error(u'----FTP清单获取失败')
        Log.error(u'---- 选择订购  [%s] [%s] %s %s %s %s FTP清单获取失败' %
                  (ymd, satID, sat, sensor, product, interval))
        return
    # 根据FTP列表获取文件上的时间信息和观测时长

    FileInfoList = GetFileInfo(F_serverList)

    # 创建轨道产品订单文件
    orderFile = os.path.join(ORDER_DIR, satID, ymd + '.txt')

    for info in FileInfoList:
        FileName = info[0]
        s_ymdhms1 = info[1]
        e_ymdhms1 = info[2]
        for timelist in combine_timeList:
            s_ymdhms2 = timelist[0]
            e_ymdhms2 = timelist[1]
            if InCrossTime(s_ymdhms1, e_ymdhms1, s_ymdhms2, e_ymdhms2):
                url = surl + '/' + s_path + '/' + FileName + '\n'
                orderList.append(url)
                break

    if len(orderList) != 0:
        #         Log.info(u'----订购成功')
        Log.info(u'---- 选择订购  [%s] [%s] %s %s %s %s 订购成功' %
                 (ymd, satID, sat, sensor, product, interval))
        WriteFile(orderFile, orderList)
    else:
        #         Log.info(u'选择订购  [%s] [%s] %s %s %s %s 失败' % (ymd, satID, sat, sensor, product, interval))
        Log.error(u'---- 选择订购  [%s] [%s] %s %s %s %s 订购失败' %
                  (ymd, satID, sat, sensor, product, interval))


def OrderGlobalProduct(satID, ymd):
    # 获取每个卫星，传感器的参数
    sat = inCfg['ORDER'][satID]['SELF_SAT']
    sensor = inCfg['ORDER'][satID]['SELF_SENSOR']
    product = inCfg['ORDER'][satID]['SELF_PRODUCT']

    # 获取全部文件
    orderList = []
    surl = inCfg['ORDER'][satID]['HOST']
    pact = surl.split('://')[0]
    host = surl.split('://')[1]
    port = inCfg['ORDER'][satID]['PORT']
    user = inCfg['ORDER'][satID]['USER']
    pawd = inCfg['ORDER'][satID]['PAWD']
    sdir = inCfg['ORDER'][satID]['SDIR']
    reg = inCfg['ORDER'][satID]['SELF_REG']
    SELF_SENSOR = inCfg['ORDER'][satID]['SELF_SENSOR']
    interval = inCfg['ORDER'][satID]['SELF_INTERVAL']
#     namerule = inCfg['ORDER'][satID]['SELF_NAMERULE']

    # 把输入日期转换到对应产品频次的日期上
#     newYmd = pb_time.ymd2ymd(satID, interval, namerule, ymd)

    # 替换字符中的%YYYY%MM%DD为当前输入时间
    stime = datetime.strptime(ymd, '%Y%m%d')
    jjj = stime.strftime('%j')
    sdir = sdir.replace('%YYYY', ymd[0:4])
    sdir = sdir.replace('%MM', ymd[4:6])
    sdir = sdir.replace('%DD', ymd[6:8])
    s_path = sdir.replace('%JJJ', jjj)
    # 创建全球产品订单文件
    orderFile = os.path.join(ORDER_DIR, satID, ymd + '.txt')
    # 获取服务器数据信息列表
    try:
        serverList = GetServerList(
            pact, host, SELF_SENSOR, user, pawd, port, s_path, reg, ymd)
    except:
        serverList = []
    # 删除list前俩行.和..
    F_serverList = [
        each + '\n' for each in serverList if not each.startswith('.')]
    # 记录获取的服务器数据清单信息
    if len(F_serverList) != 0:
        infoFile = os.path.join(ORDER_DIR, satID, ymd + '.info')
        WriteFile(infoFile, F_serverList)
    else:
        Log.error(u'---- 全球订购  [%s] [%s] %s %s %s %s FTP清单获取失败' %
                  (ymd, satID, sat, sensor, product, interval))
        return

    for Line in F_serverList:
        #         if newYmd in Line:
        FileName = Line.split()[0].strip()
        url = surl + '/' + s_path + '/' + FileName + '\n'
        orderList.append(url)

    if len(orderList) != 0:
        Log.info(u'---- 全球订购  [%s] [%s] %s %s %s %s 订购成功' %
                 (ymd, satID, sat, sensor, product, interval))
        WriteFile(orderFile, orderList)
    else:
        #         Log.info(u'----订购失败')
        Log.error(u'---- 全球订购  [%s] [%s] %s %s %s %s 订购失败' %
                  (ymd, satID, sat, sensor, product, interval))


def ReadForecastFile_area(satID, ymd):
    '''
    解析卫星和区域的预报文件
    '''
    timeList = []
    sat = inCfg['ORDER'][satID]['SELF_SAT']
    target_area = inCfg['ORDER'][satID]['TARGET_AREA']
    target_fix_area_time = inCfg['ORDER'][satID]['TARGET_AREA_TIME']
    dict_fix_area_time = {}

    for i in xrange(len(target_area)):
        dict_fix_area_time[target_area[i]] = target_fix_area_time[i]

    # 遍历区域
    for area in target_area:
        Filedir = sat + '_' + area
        FileName = sat + '_' + area + '_' + ymd + '.txt'
        ForecastFile = os.path.join(CROSS_DIR, Filedir, FileName)
        # 预报文件存在则读取
        if os.path.isfile(ForecastFile):
            fp = open(ForecastFile, 'r')
            Lines = fp.readlines()
            fp.close()
            # 解析进出时间
            for Line in Lines[10:]:
                if ymd in Line:
                    s_hms = Line.split()[1].strip()
                    e_hms = Line.split()[2].strip()
                    lat = float(Line.split()[3].strip())
                    lon = float(Line.split()[4].strip())
                    s_cross_time = datetime.strptime(
                        '%s %s' % (ymd, s_hms), '%Y%m%d %H:%M:%S')
                    e_cross_time = datetime.strptime(
                        '%s %s' % (ymd, e_hms), '%Y%m%d %H:%M:%S')
                    sunZ = pb_sat.getasol6s(
                        ymd, s_hms.replace(':', ''), lon, lat)
                    dayNight = dict_fix_area_time[area]
                    if dayNight == 'ALL':
                        timeList.append([s_cross_time, e_cross_time])
                    elif dayNight == 'NIGHT' and sunZ > 100:
                        timeList.append([s_cross_time, e_cross_time])
                    elif dayNight == 'DAY' and sunZ <= 100:
                        timeList.append([s_cross_time, e_cross_time])

    return timeList


def ReadForecastFile_fix(satID, ymd):
    '''
    解析卫星和固定点的预报文件
    '''
    timeList = []
    # 获取配置信息
    sat = inCfg['ORDER'][satID]['SELF_SAT']
    target_fix_group = inCfg['ORDER'][satID]['TARGET_FIX']
    target_fix_group_sec = inCfg['ORDER'][satID]['TARGET_FIX_SEC']
    target_fix_group_time = inCfg['ORDER'][satID]['TARGET_FIX_TIME']
    dict_fix_group_sec = {}
    dict_fix_group_time = {}

    # 固定点名和固定点的秒数对应放到字典中
    for i in xrange(len(target_fix_group)):
        dict_fix_group_sec[target_fix_group[i]] = target_fix_group_sec[i]
        dict_fix_group_time[target_fix_group[i]] = target_fix_group_time[i]
    # 拼接固定点预报文件
    Filedir = sat + '_' + 'FIX'
    FileName = sat + '_' + 'FIX' + '_' + ymd + '.txt'
    ForecastFile = os.path.join(CROSS_DIR, Filedir, FileName)
    # 预报文件存在，则读取。
    if os.path.isfile(ForecastFile):
        fp = open(ForecastFile, 'r')
        Lines = fp.readlines()
        fp.close()
        for fix_group in target_fix_group:  # 遍历固定点的组
            fixList = inCfg['FIX_LIST'][fix_group]
            for fix in fixList:  # 遍历组内的固定点
                for Line in Lines[10:]:
                    # 选择要订购的固定点
                    if fix in Line and ymd in Line:
                        # 进行时间处理，交叉时间点变为时间段
                        s_hms = Line.split()[1].strip()
                        lat = float(Line.split()[3].strip())
                        lon = float(Line.split()[4].strip())
                        cross_time = datetime.strptime(
                            '%s %s' % (ymd, s_hms), '%Y%m%d %H:%M:%S')
                        secs = int(dict_fix_group_sec[fix_group])
                        # 时间过滤类型
                        dayNight = dict_fix_group_time[fix_group]
#                         print 'time filtering flag: %s' % dayNight
                        s_cross_time = cross_time - relativedelta(seconds=secs)
                        e_cross_time = cross_time + relativedelta(seconds=secs)
                        if s_cross_time.strftime('%Y%m%d') != ymd:
                            continue
                        if e_cross_time.strftime('%Y%m%d') != ymd:
                            continue
                        sunZ = pb_sat.getasol6s(
                            ymd, s_hms.replace(':', ''), lon, lat)

                        if dayNight == 'ALL':
                            timeList.append([s_cross_time, e_cross_time])
                        elif dayNight == 'NIGHT' and sunZ > 100:
                            timeList.append([s_cross_time, e_cross_time])
                        elif dayNight == 'DAY' and sunZ <= 100:
                            timeList.append([s_cross_time, e_cross_time])
    return timeList


def ReadForecastFile_sat(satID, ymd):
    '''
    解析过卫星和卫星的预报文件
    '''

    allTimeList = []
    # 获取配置信息
    sat1 = inCfg['ORDER'][satID]['SELF_SAT']
    geoList = inCfg['SAT_TYPE']['GEO']
    target_sat = inCfg['ORDER'][satID]['TARGET_SAT']
    target_sat_sec = inCfg['ORDER'][satID]['TARGET_SAT_SEC']
#     target_sat_cross_num = inCfg['ORDER'][satID]['TARGET_SAT_NUM']
    target_sat_time = inCfg['ORDER'][satID]['TARGET_SAT_TIME']
    dict_sat_time = {}
    dict_sat_sec = {}
#     dict_sat_cross_num = {}

    # 固定点名和固定点的秒数对应放到字典中
    for i in xrange(len(target_sat)):
        dict_sat_sec[target_sat[i]] = target_sat_sec[i]
#         dict_sat_cross_num[target_sat[i]] = target_sat_cross_num[i]
        dict_sat_time[target_sat[i]] = target_sat_time[i]
    # print '！！！！！！！！！！！！！！！！！！！！！！！！！！'

    for sat2 in target_sat:
        sat2_secs = int(dict_sat_sec[sat2])
#         sat2_cross_num = int(dict_sat_cross_num[sat2])
        dayNight = dict_sat_time[sat2]
        if sat1 in geoList or sat2 in geoList:
            timeList = ReadForecastFile_GEO_LEO(
                sat1, sat2, sat2_secs, dayNight, ymd)
        else:
            # 20180510 增加过滤交叉点功能，配置保留交叉点的数量target_sat_cross_num
            timeList = ReadForecastFile_LEO_LEO(
                sat1, sat2, sat2_secs, dayNight, ymd)
        allTimeList.extend(timeList)

    return allTimeList


def jump_cross_point(crossFile, snoxFile, dayNight):
    '''
    description :增加跳点功能，并返回新的交叉内容
    crossFile： 交叉预报文件
    snoxFile： 近重合预报文件
    sat2_cross_num: 保留个数
    '''
#     Lines = []
    Lines1 = []
    Lines2 = []
    save_cross_num = 8  # 订购保留8个

    if os.path.isfile(crossFile):

        fp = open(crossFile, 'r')
        bufs = fp.readlines()
        fp.close()
        # 获取长度不包含头信息
        bodyLines = bufs[10:]

        # 黑白过滤
        dayNightLines = []
        print u'黑白过滤前 交叉点数量 %d' % len(bodyLines)
        for Line in bodyLines:
            ymd = Line.split()[0].strip()
            hms = Line.split()[1].strip()
            lat = float(Line.split()[2].strip())
            lon = float(Line.split()[3].strip())
            sunZ = pb_sat.getasol6s(ymd, hms.replace(':', ''), lon, lat)

            if dayNight == 'ALL':
                dayNightLines.append(Line)
            elif dayNight == 'NIGHT' and sunZ > 100:
                dayNightLines.append(Line)
            elif dayNight == 'DAY' and sunZ <= 100:
                dayNightLines.append(Line)
            else:
                pass

        lens = len(dayNightLines)
        print u'黑白过滤后 交叉点数 %d' % lens

        half_cross_num = save_cross_num / 2
        if lens <= save_cross_num:
            Lines1 = dayNightLines
            print u'<= %d, 全部保留' % save_cross_num
        else:
            Lines1 = dayNightLines[:half_cross_num] + \
                dayNightLines[-half_cross_num:]
            print u'> %d, 保留前%d,后%d' % (save_cross_num, half_cross_num, half_cross_num)

#         if lens <= save_cross_num:
#             Lines1 = dayNightLines
#         else:
#             Rest = lens % save_cross_num
#             if save_cross_num - Rest == 1:  # 满足间隔取点步长增加条件
#                 step = int(lens / save_cross_num) + 1
#             else:
#                 step = int(lens / save_cross_num)
#             newBodyLines = dayNightLines[::step]
#             # 间隔取点后还有多余的丢弃
#             Lines1 = newBodyLines[:save_cross_num]
#         print '间隔取点后 交叉点数 %d' % len(Lines1)

    # 近重合
    if os.path.isfile(snoxFile):
        fp = open(snoxFile, 'r')
        bufs = fp.readlines()
        fp.close()
        # 获取长度
        Lines2 = bufs[10:]
    return Lines1 + Lines2


def ReadForecastFile_LEO_LEO(sat1, sat2, sat2_secs, dayNight, ymd):

    # 本模块于2017-12-14添加了snox的订购。订购时应注意相同卫星对的情况下，cross与snox内卫星前后顺序是否一致。
    timeList = []
    # 拼接预报文件
    Filedir = sat1 + '_' + sat2
    FileName = sat1 + '_' + sat2 + '_' + ymd + '.txt'

    # 拼接snox预报文件。
    FileName2 = sat1 + '_' + sat2 + '_' + 'SNOX' + '_' + ymd + '.txt'
    crossFile = os.path.join(CROSS_DIR, Filedir, FileName)
    snoxFile = os.path.join(SNOX_DIR, Filedir, FileName2)

    if not os.path.isfile(crossFile):  # 不存在则调换卫星顺序
        Filedir = sat2 + '_' + sat1
        FileName = sat2 + '_' + sat1 + '_' + ymd + '.txt'
        crossFile = os.path.join(CROSS_DIR, Filedir, FileName)

    if not os.path.isfile(snoxFile):  # 不存在则调换卫星顺序
        Filedir = sat2 + '_' + sat1
        FileName2 = sat2 + '_' + sat1 + '_' + 'SNOX' + '_' + ymd + '.txt'
        snoxFile = os.path.join(SNOX_DIR, Filedir, FileName2)

    # 读取交叉点内容并跳点
    crossLines = jump_cross_point(
        crossFile, snoxFile, dayNight)

    if len(crossLines) == 0:
        print u'cross nums is 0'
        return timeList

    for Line in crossLines:
        if ymd in Line:  # 订购日期所在行
            if SatLocation(crossFile, sat1) == 1:  # 如果订购卫星在前
                s_hms = Line.split()[1].strip()
#                 lat = float(Line.split()[2].strip())
#                 lon = float(Line.split()[3].strip())
                cross_time = datetime.strptime(
                    '%s %s' % (ymd, s_hms), '%Y%m%d %H:%M:%S')
            elif SatLocation(crossFile, sat1) == 2:  # 如果订购卫星在后
                s_hms = Line.split()[4].strip()
#                 lat = float(Line.split()[5].strip())
#                 lon = float(Line.split()[6].strip())
                cross_time = datetime.strptime(
                    '%s %s' % (ymd, s_hms), '%Y%m%d %H:%M:%S')
            else:
                continue

            # 目标卫星阈值秒
            # secs = int(dict_sat_sec[sat2])
            s_cross_time = cross_time - relativedelta(seconds=sat2_secs)
            e_cross_time = cross_time + relativedelta(seconds=sat2_secs)
            if s_cross_time.strftime('%Y%m%d') != ymd:
                continue
            if e_cross_time.strftime('%Y%m%d') != ymd:
                continue
            timeList.append([s_cross_time, e_cross_time])
    return timeList


def ReadForecastFile_GEO_LEO(sat1, sat2, sat2_secs, dayNight, ymd):
    timeList = []
    # match_time = ymd[0:4] + '.' + ymd[4:6] + '.' + ymd[6:8]
    # 拼接预报文件
    Filedir = sat1 + '_' + sat2
    FileName = sat1 + '_' + sat2 + '_' + ymd + '.txt'
    ForecastFile = os.path.join(CROSS_DIR, Filedir, FileName)
    if not os.path.isfile(ForecastFile):  # 不存在则调换卫星顺序
        Filedir = sat2 + '_' + sat1
        FileName = sat2 + '_' + sat1 + '_' + ymd + '.txt'
        ForecastFile = os.path.join(CROSS_DIR, Filedir, FileName)
        if not os.path.isfile(ForecastFile):  # 调换顺序后还不存在则跳过
            return timeList

    fp = open(ForecastFile, 'r')
    Lines = fp.readlines()
    fp.close()
    for Line in Lines[10:]:
        if ymd in Line:  # 订购日期所在行
            s_hms = Line.split()[1].strip()
            e_hms = Line.split()[2].strip()
            lat = float(Line.split()[3].strip())
            lon = float(Line.split()[4].strip())
            cross_time1 = datetime.strptime(
                '%s %s' % (ymd, s_hms), '%Y%m%d %H:%M:%S')
            cross_time2 = datetime.strptime(
                '%s %s' % (ymd, e_hms), '%Y%m%d %H:%M:%S')
            # 目标卫星阈值秒
            s_cross_time = cross_time1 - relativedelta(seconds=sat2_secs)
            e_cross_time = cross_time2 + relativedelta(seconds=sat2_secs)
            if s_cross_time.strftime('%Y%m%d') != ymd:
                continue
            if e_cross_time.strftime('%Y%m%d') != ymd:
                continue
            sunZ = pb_sat.getasol6s(
                ymd, s_hms.replace(':', ''), lon, lat)

            if dayNight == 'ALL':
                timeList.append([s_cross_time, e_cross_time])
            elif dayNight == 'NIGHT' and sunZ > 100:
                timeList.append([s_cross_time, e_cross_time])
            elif dayNight == 'DAY' and sunZ <= 100:
                timeList.append([s_cross_time, e_cross_time])
    return timeList


def SatLocation(ForecastFile, sat):
    '''
    判断要处理的卫星使用的预报文件是在前还是在后
    '''
    FileName = os.path.split(ForecastFile)[1]
    sat1 = FileName.split('_')[0].strip()
    sat2 = FileName.split('_')[1].strip()
    if sat == sat1:  # 在前
        return 1
    elif sat == sat2:  # 在后
        return 2
    else:
        return 0


def CombineTimeList(TimeList):
    # 将时间段list中有重叠的时间段进行融合为新的时间段
    newTimeList = []
    # 默认排序,升序
    TimeList.sort()
    # 标记有时间融合的时间
    stime = TimeList[0][0]
    etime = TimeList[0][1]
    for i in xrange(1, len(TimeList), 1):
        if TimeList[i][1] <= etime:
            continue
        elif TimeList[i][0] <= etime <= TimeList[i][1]:
            etime = TimeList[i][1]
        elif TimeList[i][0] > etime:
            newTimeList.append([stime, etime])
            stime = TimeList[i][0]
            etime = TimeList[i][1]

    newTimeList.append([stime, etime])

    return newTimeList


def InCrossTime(s_ymdhms1, e_ymdhms1, s_ymdhms2, e_ymdhms2):
    '''
    判断俩个时间段是否有交叉
    '''
    if s_ymdhms2 <= s_ymdhms1 <= e_ymdhms2:
        return True
    elif s_ymdhms2 <= e_ymdhms1 <= e_ymdhms2:
        return True
    elif s_ymdhms2 >= s_ymdhms1 and e_ymdhms2 <= e_ymdhms1:
        return True
    else:
        return False


def GetServerList(pact, host, SELF_SENSOR, user, pawd, port, s_path, regList, ymd):
    '''
    获取服务器上指定目录的数据列表
    格式：文件名  大小(字节)
    '''
#      pact, host, user, pawd, port, s_path, ymd
    ftpList = []
    # 读取协议信息
    if pact == 'sftp':
        ftpList = use_sftp_getList(
            host, user, pawd, port, s_path, regList, ymd)
    elif pact == 'ftp':
        ftpList = use_ftp_getList(host, user, pawd, port, s_path, regList, ymd)
    elif pact == 'https'and SELF_SENSOR == 'MODIS':
        ftpList = use_https_getList_MODIS(
            pact, host, SELF_SENSOR, user, pawd, port, s_path, regList, ymd)
    elif pact == 'http' or pact == 'https':
        ftpList = use_http_getList(
            pact, host, user, pawd, port, s_path, regList, ymd)
    else:
        Log.info(u'----不支持此协议:%s' % pact)

    return ftpList


def use_sftp_getList(host, user, pawd, port, s_path, regList, ymd):

    FileList = []
    try:
        tt = paramiko.Transport((host, int(port)))
        tt.connect(username=user, password=pawd)
        sftp = paramiko.SFTPClient.from_transport(tt)
        sftp.chdir(s_path)
        Lines = sftp.listdir(s_path)
        # 获取目录下所有文件目录
        for FileName in Lines:
            for reg in regList:  # 符合正则的进行处理
                m = re.match(reg, FileName)
                if m is not None:
                    mstat = sftp.lstat(FileName)
                    newLine = FileName + ' ' + str(mstat.st_size)
                    FileList.append(newLine)
        tt.close()
    except Exception as e:
        # print '#########', host, user, pawd, port, s_path, regList, ymd
        # print('----%s' % str(e))
        print('----%s----%s' % (str(e), host))

    return FileList


def use_ftp_getList(host, user, pawd, port, s_path, regList, ymd):

    FileList = []

    class MySession(ftplib.FTP):

        def __init__(self, FTP, userid, password, port):
            """Act like ftplib.FTP's constructor but connect to another port."""
            ftplib.FTP.__init__(self)
            self.connect(FTP, port)
            self.login(userid, password)

    try:
        FTP = ftputil.FTPHost(host, user, pawd, port=port,
                              session_factory=MySession)
        FTP.chdir(s_path)
        nameList = FTP.listdir(FTP.curdir)
        for name in nameList:
            for reg in regList:  # 符合正则的进行处理
                m = re.match(reg, name)
                if m is not None:
                    nameClass = pb_name.nameClassManager()
                    info = nameClass.getInstance(name)
                    if info is None:
                        continue
                    if info.dt_s.strftime('%Y%m%d') != ymd:
                        continue
                    stat = FTP.lstat(name)
                    size = stat[6]
                    Line = name + ' ' + str(size)
                    FileList.append(Line)
        FTP.close()
    except Exception as e:
        print (u'----%s' % str(e))

    return FileList


def use_https_getList_MODIS(pact, host, SELF_SENSOR, user, pawd, port, s_path, regList, ymd):

    FileList = []
    src = pact + '://' + host + '/' + s_path
    tok = 'FEB56222-63BA-11E8-B399-F01EAE849760'  # 应用密钥
    headers = {'user-agent': 'tis/download.py_1.0--' +
               sys.version.replace('\n', '').replace('\r', '')}
    headers['Authorization'] = 'Bearer ' + tok
    fh = urllib2.urlopen(urllib2.Request('%s.csv' % src, headers=headers))
    files = [f for f in csv.DictReader(
        StringIO(fh.read()), skipinitialspace=True)]
    for f in files:
        try:
            filesize = int(f['size'])
            Name = f['name']
            Line = Name + ' ' + str(filesize)
            FileList.append(Line)
        except Exception, e:
            print "ERROR: ", e
            FileList = []

    return FileList


def use_http_getList(pact, host, user, pawd, port, s_path, regList, ymd):

    FileList = []
    url = '%s://%s:%s' % (pact, host, port) + s_path
    html = getHtml(url)
    if html is None:
        return FileList
    dm = DM()
    dm.feed(html)
    dm.close()
    htmlList = dm.getStr()
    for Name in htmlList:
        for reg in regList:
            m = re.match(reg, Name)
            if m is not None:
                try:
                    nameClass = pb_name.nameClassManager()
                    info = nameClass.getInstance(Name)
                    if info is None:
                        continue
                    if info.dt_s.strftime('%Y%m%d') != ymd:
                        continue

                    # huangyj  2017/03/28  由于nasa无法通过身份验证，暂时通过网页抓取数据的大小
                    size = GetFileSize(html, Name)
#                     f = urllib2.urlopen(url + '/' + Name)
#                     if "Content-Length" in f.headers:
#                         print f.headers
#                         size = int (f.headers["Content-Length"])
#                     else:
#                         # 如果没有Length信息则把长度设置为0，无法做完整性检查
# #                         size = len (f.read ())
#                         size = 0
                    Line = Name + ' ' + str(size)
                    FileList.append(Line)
                except Exception, e:
                    print "ERROR: ", e
                    FileList = []

    return FileList


def GetFileSize(html, FileName):
    Filestring = re.findall(r'<a.*?href="%s">%s.*<\/td>' %
                            (FileName, FileName), html)
    if len(Filestring) <= 0:
        return 0

    for Fstring in Filestring:
        a = Fstring
        b = a.split('<td align="right">')[-1]
        FileSize = b.split('</td>')[0]
        break

    if 'G' not in FileSize and 'M' not in FileSize and 'K' not in FileSize:
        return int(float(FileSize))
    fileSizenounit = FileSize.strip()[:-1]
    Unit = FileSize.strip()[-1]
    if Unit in 'G':
        return int(float(fileSizenounit) * 1000 * 1000 * 1024)
    if Unit in 'M':
        return int(float(fileSizenounit) * 1000 * 1000)
    if Unit in 'K':
        return int(float(fileSizenounit) * 1000)


class DM(HTMLParser):

    '''
    网页解析
    '''

    def __init__(self):
        self.strlst = []
        self.a = False
        HTMLParser.__init__(self)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.a = True

    def handle_endtag(self, tag):
        if tag == 'a':
            self.a = False

    def handle_data(self, data):
        if self.a:
            if not data.strip() == '':
                self.strlst.append(data.strip())

    def getStr(self):
        return self.strlst


def getHtml(url):
    '''
    获得网页
    '''
#     opener = urllib2.build_opener(
#         urllib2.HTTPHandler(),
#         urllib2.HTTPSHandler(),
#         urllib2.ProxyHandler({'https': 'http://user:pass@proxy:3128'}))
#     urllib2.install_opener(opener)
#
#     try:
#         req = urllib2.Request(url)
#         resp = urllib2.urlopen(req)
#     except Exception, e:
#         Log.error(e)
#         return None
    user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows XP)'
    values = {'name': 'Michael Foord',
              'location': 'Northampton',
              'language': 'Python'}
    headers = {'User-Agent': user_agent}
    data = urllib.urlencode(values)
    try:
        req = urllib2.Request(url, data, headers)
        resp = urllib2.urlopen(req)
    except Exception as e:
        print (u'----%s' % str(e))
        return None
    html = resp.read()
    resp.close()
    return html


def GetFileInfo(FtpList):
    '''
    通过正则类对数据进行解析
    '''
    FileInfoList = []
    for ftpList in FtpList:
        Filename = ftpList.split()[0].strip()
        nameClass = pb_name.nameClassManager()
        info = nameClass.getInstance(Filename)
        if info is None:
            continue

        FileInfoList.append([Filename, info.dt_s, info.dt_e])

    return FileInfoList


def WriteFile(filename, lines):
    '''
    # 写文件
    :param filename:
    :param lines:
    :return:
    '''
    mdir = os.path.dirname(filename)
    if not os.path.isdir(mdir):
        os.makedirs(mdir)
    if os.path.isfile(filename):
        # 删除原有的订单文件，重新写入订单
        os.unlink(filename)

    fp = open(filename, 'w')
    fp.writelines(lines)
    fp.close()


# 程序全局入口 ##############################
args = sys.argv[1:]
help_info = \
    u'''
        【参数1】：08026A_01_02 (卫星编号)
        【参数2】：yyyymmdd-yyyymmdd
    '''
if '-h' in args:
    print help_info
    sys.exit(-1)

# 获取程序所在位置，拼接配置文件
MainPath, MainFile = os.path.split(os.path.realpath(__file__))
ProjPath = os.path.dirname(MainPath)
# cfgName = MainFile.split('.')[0]
cfgFile = os.path.join(MainPath, 'dm_odm.cfg')
# 配置不存在预警
if not os.path.isfile(cfgFile):
    print (u'配置文件不存在 %s' % cfgFile)
    sys.exit(-1)
# 载入配置文件
inCfg = ConfigObj(cfgFile)

# 初始化日志
LogPath = inCfg['PATH']['OUT']['LOG']
Log = LogServer(LogPath)

# 读取需要的信息
CROSS_DIR = inCfg['PATH']['IN']['CROSS']
SNOX_DIR = inCfg['PATH']['IN']['SNOX']
ORDER_DIR = inCfg['PATH']['OUT']['ORDER']
ID_DIR = inCfg['PATH']['OUT']['ID']

MAIL_HOST = inCfg['MAIL']['MAIL_HOST']
MAIL_USER = inCfg['MAIL']['MAIL_USER']
MAIL_PAWD = inCfg['MAIL']['MAIL_PAWD']

use_proxy = inCfg['PROXY']['use_proxy']
PROXY_HOST = inCfg['PROXY']['host']
PROXY_PORT = int(inCfg['PROXY']['port'])


PROXY_USER = inCfg['PROXY']['user']
PROXY_PAWD = inCfg['PROXY']['pawd']

NUM = inCfg['ORDER'].keys()

# 启动socket服务,防止多实例运行
port = 9850
sserver = SocketServer()
if sserver.createSocket(port) == False:
    Log.error(u'----已经有一个实例在实行')
    sys.exit(-1)

# 判断系统类型
if 'nt' in os.name:
    OSTYPE = 'windows'
elif 'posix' in os.name:
    OSTYPE = 'linux'
else:
    Log.info('不识别的系统类型')
    sys.exit(-1)

# 设置代理信息，如果服务器无法连接外网需要设置代理连接
if 'ON' in use_proxy:
    socks.set_default_proxy(socks.SOCKS5, PROXY_HOST,
                            PROXY_PORT, True, PROXY_USER, PROXY_PAWD)
    socket.socket = socks.socksocket

# 获取开机线程的个数，开启线程池。获取订单对时间和编号进行并行操作
threadNum = inCfg['TOOL']['thread']
pool = threadpool.ThreadPool(int(threadNum))

# 手动执行跟2个参数，卫星明和时间段
if len(args) == 2:
    Log.info(u'手动运行订购程序 -----------------------------')

    satID = args[0]  # 卫星全名
    str_time = args[1]  # 程序执行时间范围

    # 进行时间的解析，由YYYYMMDD-YYYYMMDD 转为datetime类型的开始时间和结束时间
    date_s, date_e = pb_time.arg_str2date(str_time)

    # 重新根据数据规则定义时间清单
    NumDateDict1 = {}
    NumDateDict2 = {}
    # 定义参数List，传参给线程池
    args_List = []
    while date_s <= date_e:
        # 时间转换
        ymd = date_s.strftime('%Y%m%d')
        date_s = date_s + relativedelta(days=1)
        MODE_O = inCfg['ORDER'][satID]['MODE_O']
        if 'ON' not in MODE_O:
            continue

        interval = inCfg['ORDER'][satID]['SELF_INTERVAL']
        namerule = inCfg['ORDER'][satID]['SELF_NAMERULE']
        # 定义俩个字典的List
        if satID not in NumDateDict1.keys():
            NumDateDict1[satID] = []
            NumDateDict2[satID] = []
        newYmd = pb_time.ymd2ymd(satID, interval, namerule, ymd)
        # 把新时间放到字段中
        NumDateDict1[satID].append(newYmd)
    # 把第一个字典的时间去重，放到第二个字典中
    for satID in NumDateDict1.keys():
        NumDateDict2[satID] = sorted(
            set(NumDateDict1[satID]), key=NumDateDict1[satID].index)
    print NumDateDict2
    # 放入线程字典
    for satID in NumDateDict2.keys():
        for ymd in NumDateDict2[satID]:
            # 定义线程池调用函数的参数。单个参数定义一个list，多个参数根据字典格式进行传参
            dict_List = {'satID': satID, 'ymd': ymd}
            args_List.append((None, dict_List))

    # 存在卫星数据 ，进行线程的调用
    if len(args_List) > 0:
        requests = threadpool.makeRequests(run, args_List, None)
        [pool.putRequest(req) for req in requests]
        pool.wait()

elif len(args) == 0:
    Log.info(u'自动运行订购程序 -----------------------------')
    rolldays = inCfg['CROND']['rolldays']
    satLst = inCfg['ORDER'].keys()
    # 重新根据数据规则定义时间清单
    NumDateDict1 = {}
    NumDateDict2 = {}
    # 定义参数List，传参给线程池
    args_List = []

    # 开始滚动其余时间
    for satID in satLst:
        MODE_O = inCfg['ORDER'][satID]['MODE_O']
        if 'ON' not in MODE_O:
            continue
        interval = inCfg['ORDER'][satID]['SELF_INTERVAL']
        namerule = inCfg['ORDER'][satID]['SELF_NAMERULE']
        # 定义俩个字典的List
        if satID not in NumDateDict1.keys():
            NumDateDict1[satID] = []
            NumDateDict2[satID] = []
        for rdays in rolldays:
            ymd = (datetime.utcnow() -
                   relativedelta(days=int(rdays))).strftime('%Y%m%d')
            newYmd = pb_time.ymd2ymd(satID, interval, namerule, ymd)
            # 把新时间放到字段中
            NumDateDict1[satID].append(newYmd)
    # 把第一个字典的时间去重，放到第二个字典中
    for satID in NumDateDict1.keys():
        NumDateDict2[satID] = sorted(
            set(NumDateDict1[satID]), key=NumDateDict1[satID].index)
    print NumDateDict2
    # 放入线程字典
    for satID in NumDateDict2.keys():
        for ymd in NumDateDict2[satID]:
            # 定义线程池调用函数的参数。单个参数定义一个list，多个参数根据字典格式进行传参
            dict_List = {'satID': satID, 'ymd': ymd}
            args_List.append((None, dict_List))
    # 存在卫星数据 ，进行线程的调用
    if len(args_List) > 0:
        requests = threadpool.makeRequests(run, args_List, None)
        [pool.putRequest(req) for req in requests]
        pool.wait()
