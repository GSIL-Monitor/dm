# coding: utf-8

import shutil
import sys
import os
from configobj import ConfigObj
from PB import pb_name
from PB.CSC.pb_csc_console import LogServer, SocketServer
import gzip
__author__ = 'wangpeng'

'''
FileName:     dm_odm_move.py
Description:  迁移卫星数据
Author:       wangpeng
Date:         2015-08-21
version:      1.0.0.050821_beat
Input:        dm_odm.cfg 编号信息
Output:       (^_^)
'''


def run(num):
    sat = inCfg['ORDER'][num]['SELF_SAT']
    sensor = inCfg['ORDER'][num]['SELF_SENSOR']
    product = inCfg['ORDER'][num]['SELF_PRODUCT']
    interval = inCfg['ORDER'][num]['SELF_INTERVAL']

    # 遍历要迁移的数据，生成迁移的数据列表，存放在字典中，用时间当作key
    TMP_DIR = os.path.join(T_DATA, num)
    if sat == "GCOM":
        Dict_GCOM = MatchMoveList(TMP_DIR)
        for Key in Dict_GCOM.keys():
            for value in Dict_GCOM[Key]:
                FilePath = os.path.join(TMP_DIR, value)
                FilePath = FilePath.strip('\n')
                g = gzip.GzipFile(mode="rb", fileobj=open(FilePath, 'rb'))
                filename = value[:-4]
                Spath = os.path.join(TMP_DIR, filename)
                try:
                    open(Spath, "wb").write(g.read())
                except Exception as e:
                    continue
                finally:
                    g.close()
                    os.remove(FilePath)

    # 把每天的数据记录到迁移记录文件中
    Dict = MatchMoveList(TMP_DIR)
    for ymd in Dict.keys():
        Log.info(u'迁移 [%s] [%s] %s %s %s %s' %
                 (ymd, num, sat, sensor, product, interval))
        mvrecFile = os.path.join(MVREC, num, ymd + '.txt')
        mvrecDir = os.path.dirname(mvrecFile)
        if not os.path.isdir(mvrecDir):
            os.makedirs(mvrecDir)
        # 记录迁移信息
        Write(mvrecFile, Dict[ymd])

        # 开始迁移数据
        i = 0
        j = 0
        for fileName in Dict[ymd]:
            tempFile = os.path.join(T_DATA, num, fileName.strip())
            LocalDir = os.path.join(
                S_DATA, sat, sensor, product, interval, ymd[:6])
            LocalFile = os.path.join(LocalDir, fileName.strip())
            if not os.path.isdir(LocalDir):
                os.makedirs(LocalDir)

            try:
                if os.path.isfile(LocalFile):
                    os.unlink(LocalFile)
                shutil.move(tempFile, LocalFile)
                Log.info(u'----%s 成功 ' % fileName.strip())
                i = i + 1
            except Exception, e:
                Log.error(u'----%s 失败' % fileName.strip())
                print (e)
                j = j + 1
                continue
        Log.info(u'----统计信息 成功: %s  失败: %s' % (i, j))


def Write(FileName, newLines):
    allLines = []
    FilePath = os.path.dirname(FileName)
    if not os.path.exists(FilePath):
        os.makedirs(FilePath)

    if os.path.isfile(FileName):
        fp = open(FileName, 'r')
        oldLines = fp.readlines()
        fp.close()

        # 已有数据
        for Line in oldLines:
            if Line not in allLines:
                allLines.append(Line)
        # 新的数据
        for Line in newLines:
            if Line not in allLines:
                allLines.append(Line)
        fp = open(FileName, 'w')
        fp.writelines(allLines)
        fp.close()
    else:
        fp = open(FileName, 'w')
        fp.writelines(newLines)
        fp.close()


def MatchMoveList(mdir):
    # 遍历要迁移的目录
    Dict = {}
    if not os.path.isdir(mdir):
        return Dict
    Lst = sorted(os.listdir(mdir), reverse=False)
    # print mdir
    for line in Lst:
        FullPath = os.path.join(mdir, line)
        if os.path.isfile(FullPath):

            fileName = line.strip()
            if '.lock' in fileName:
                continue
            else:
                nameClass = pb_name.nameClassManager()
                info = nameClass.getInstance(fileName)
                if info is None:
                    continue
                ymd = info.dt_s.strftime('%Y%m%d')
                # hms = info.hms
                # sec = info.totalSec
                # 定义key为字典
                if ymd not in Dict.keys():
                    Dict[ymd] = []
                Dict[ymd].append(fileName + '\n')
    return Dict


# 程序全局入口

# 获取程序参数接口
args = sys.argv[1:]
help_info = \
    u'''
    【参数】 无
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

# 启动socket服务,防止多实例运行
port = 9803
sserver = SocketServer()
if sserver.createSocket(port) == False:
    Log.info(u'----已经有一个实例在实行')
    sys.exit(-1)

# 读取目录信息
T_DATA = inCfg['PATH']['OUT']['T_DATA']
MVREC = inCfg['PATH']['OUT']['MVREC']
S_DATA = inCfg['PATH']['OUT']['S_DATA']

Log.info(u'运行数据迁移程序 -----------------------------')

# 获取编号
satLst = inCfg['ORDER']
for satID in satLst:
    run(satID)
