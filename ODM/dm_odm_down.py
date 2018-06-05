# coding: utf-8
__author__ = 'wangpeng'

'''
FileName:     dm_odm_down.py
Description:  根据订单下载数据
Author:       wangpeng
Date:         2015-08-23
version:      1.0.0.050823_beat
Input:        args1:开始时间-结束时间  [YYYYMMDD-YYYYMMDD]
Output:       (^_^)
'''
import os, sys, time
from datetime import datetime
from configobj import ConfigObj
import threadpool, subprocess
from dateutil.relativedelta import relativedelta
from PB import pb_time
from PB.CSC.pb_csc_console import LogServer, SocketServer

def run(satID, ymd):

    sat = inCfg['ORDER'][satID]['SELF_SAT']
    sensor = inCfg['ORDER'][satID]['SELF_SENSOR']
    product = inCfg['ORDER'][satID]['SELF_PRODUCT']
    interval = inCfg['ORDER'][satID]['SELF_INTERVAL']
    namerule = inCfg['ORDER'][satID]['SELF_NAMERULE']

    # 获取对应产品的真正日期
    newYmd = pb_time.ymd2ymd(satID, interval, namerule, ymd)
    orderFile = os.path.join(ORDER, satID, newYmd + '.txt')
    infoFile = os.path.join(ORDER, satID, newYmd + '.info')
    mvrecFile = os.path.join(MVREC, satID, newYmd + '.txt')
    tmpPath = os.path.join(T_DATA, satID)
    # 创建临时目录
    if not os.path.isdir(tmpPath):
        os.makedirs(tmpPath)

    # 检查缺失的订单文件
    plan_nums, orderList, sizeList = CheckLost(satID, newYmd, orderFile, infoFile, mvrecFile)

    Log.info(u'开始下载  [%s] [%s] %s %s %s %s 计划下载: %s  缺失数量: %s' % (ymd, satID, sat, sensor, product, interval, len(plan_nums), len(orderList)))
    if len(plan_nums) == 0:
        return
    if len(orderList) <= 0:
        return

    # 下载缺失的订单文件
    conf_List = []
    for i in xrange(len(orderList)):
        url = orderList[i].strip()
        plan_size = int(sizeList[i])

        dict_List = {'satID':satID, 'url':url, 'plan_size':plan_size}
        conf_List.append((None, dict_List))

    # 将参数List提交到线程池
    if len(conf_List) > 0:
        requests = threadpool.makeRequests(download, conf_List, None)
        [pool.putRequest(req) for req in requests]
        pool.wait()


def download(satID, url, plan_size):
    '''
    根据订单下载文件
    :param satID:         数据编号
    :param orderList:   订单列表
    :param sizeList:    数据大小列表
    :return:
    '''
    sat = inCfg['ORDER'][satID]['SELF_SAT']
    sensor = inCfg['ORDER'][satID]['SELF_SENSOR']
    product = inCfg['ORDER'][satID]['SELF_PRODUCT']
    interval = inCfg['ORDER'][satID]['SELF_INTERVAL']

    sizeList = [-1] * 10
    # 协议类型
    surl = inCfg['ORDER'][satID]['HOST']
    user = inCfg['ORDER'][satID]['USER']
    pawd = inCfg['ORDER'][satID]['PAWD']
    pact = surl.split('://')[0]

    # 获取下载工具参数信息
    retry = inCfg['TOOL']['retry']
    retry_delay = inCfg['TOOL']['retry_delay']
    timeout = inCfg['TOOL']['timeout']
    limit_rate = inCfg['TOOL']['limit_rate']

    # 从url地址中获取文件名称
    fileName = os.path.split(url)[1]
    # 正式文件
    tmpFile = os.path.join(T_DATA, satID, fileName)
    # 临时文件
    tmpFile_lock = os.path.join(T_DATA, satID, fileName + '.lock')

    Fullmbin = ""
    if pact == 'sftp':
        mbin = inCfg['TOOL']['curl']
        # 拼接上级目录下的url路径
        Fullmbin = os.path.join(ProjPath, 'BIN', OSTYPE, mbin)
        # 封装下载工具参数，目前是wget的封装方法
        cmd = '''%s -k -u %s:%s \
                 --retry %s --retry-delay %s --connect-timeout %s --limit-rate %s
                 -s  -C - -#\
                 -o %s %s ''' \
              % (Fullmbin, user, pawd, retry, retry_delay, timeout, limit_rate, tmpFile_lock, url)
    elif pact == 'ftp' or pact == 'http' or pact == 'https':
        mbin = inCfg['TOOL']['wget']
        # 封装下载工具参数，目前是wget的封装方法
        # 拼接上级目录下的wget路径
        Fullmbin = os.path.join(ProjPath, 'BIN', OSTYPE, mbin)
        cmd = '''%s --user=%s --password=%s --tries=%s --no-check-certificate --timeout=%s \
                --waitretry=%s  --limit-rate=%s \
                -c --no-parent -nd -nH -q \
                -O %s %s  ''' \
              % (Fullmbin, user, pawd, retry, timeout, retry_delay, limit_rate, tmpFile_lock, url)
    # 下载工具未配置则退出
    if not os.path.isfile(Fullmbin):
        print (u'----下载工具不存在 %s' % Fullmbin)
        return

    # 获取临时文件大小
    if not os.path.isfile(tmpFile):
        tmpFileSize = 0
    else:
        tmpFileSize = os.path.getsize(tmpFile)
    # 如果下载完成为迁移则跳过并删除lock文件
    if tmpFileSize >= plan_size:
        Log.info(u'---- [%s] [%s] %s %s %s %s %s 文件存在' % (ymd, satID, sat, sensor, product, interval, fileName))
        if os.path.isfile(tmpFile_lock):
            os.unlink(tmpFile_lock)
        return

    # 获取临时lock文件大小
    if not os.path.isfile(tmpFile_lock):
        lockFileSize = 0
    else:
        lockFileSize = os.path.getsize(tmpFile_lock)

    # 如果本地文件不完整，则下载
    if lockFileSize < plan_size:
        try:
            P1 = subprocess.Popen(cmd.split())
        except Exception, e:
            Log.error(e)
            return
        # 获取后台命令是否运行成功返回
        while (P1.poll() == None):
            # 循环获取临时lock文件大小，来判断是否卡住
            if not os.path.isfile(tmpFile_lock):
                lockSize = 0
            else:
                lockSize = os.path.getsize(tmpFile_lock)

            sizeList.append(lockSize)
            sizeList.pop(0)
            # print sizeList[0], sizeList[-1], plan_size
            if sizeList[0] == sizeList[-1]:
                P1.kill()
                Log.error(u'---- [%s] [%s] %s %s %s %s %s 进程已经被杀死' % (ymd, satID, sat, sensor, product, interval, fileName))
                break
            time.sleep(15)
        # P1.kill()
        P1.wait()

    # 下载结束后，第二次获取临时lock文件大小
    if not os.path.isfile(tmpFile_lock):
        lockFileSize = 0
    else:
        lockFileSize = os.path.getsize(tmpFile_lock)

    # 下载失败，则清理lock文件
    if lockFileSize == 0:
        os.unlink(tmpFile_lock)

    # 下载成功，重新命名
    if lockFileSize >= plan_size:
        os.rename(tmpFile_lock, tmpFile)
        Log.info(u'---- [%s] %s 下载成功' % (ymd, fileName))
    else:
        Log.error(u'---- [%s] %s 下载失败' % (ymd, fileName))


def CheckLost(satID, ymd, orderFile, infoFile, mvrecFile):

    orderList1 = []
    orderList2 = []
    sizeList = []

    # print orderFile
    if not os.path.isfile(orderFile):
#         print(u'----订单文件不存在')
        return [], [], []
    else:
        fp = open(orderFile, 'r')
        orderLines = fp.readlines()
        fp.close()

    if not os.path.isfile(infoFile):
#         print(u'----服务器清单文件不存在')
        return [], [], []
    else:
        fp = open(infoFile, 'r')
        ftpLines = fp.readlines()
        fp.close()

    if os.path.isfile(mvrecFile):
        fp = open(mvrecFile, 'r')
        mvrecLines = fp.readlines()
        fp.close()
    else:
        mvrecLines = []
    # 第一轮看是否有迁移走的记录，有则删除此条记录
    for url in orderLines:
        fileName = os.path.split(url)[1].strip()
        # 解析迁移记录信息,存在的就是已经下载完成并迁移走了
        if inList(fileName, mvrecLines):
            continue
        orderList1.append(url)

    # 第二轮看是否在临时目录并且已经下载完成
    for url in orderList1:
        fileName = os.path.split(url)[1].strip()
        # 在FTP清单中找到此文件大小
        PlanSize = getPlanSize(fileName, ftpLines)

        if PlanSize == 0:
            continue
        tmpFile = os.path.join(T_DATA, satID, fileName)
        # 获取临时目录里文件是否存在以及存在的大小
        if os.path.isfile(tmpFile):
            RealSize = os.path.getsize(tmpFile)
        else:
            RealSize = 0
        # 数据在临时目录中并且下载完成
        if int(RealSize) >= int(PlanSize):
            continue
        orderList2.append(url)
        sizeList.append(PlanSize)

    return orderLines, orderList2, sizeList


def getPlanSize(fileName, ftpList):
    PlanSize = 0
    for ftpInfo in ftpList:
        if fileName in ftpInfo:
            PlanSize = ftpInfo.split()[1].strip()
            break
    return int(PlanSize)


def inList(mstr, mlist):
    flag = -1
    if len(mlist) == 0:
        return False

    # 遍历该文件是否存在迁移记录目录中
    for line in mlist:
        if 'GCRSO-SCRIS_npp_d' in mstr:
            if mstr[:48] in line.strip():
                flag = 0
        elif mstr in line.strip():
            flag = 0
    if flag == 0:
        return True
    else:
        return False



######################### 程序全局入口 ##############################

# 获取程序参数接口
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

# 读取配置文件信息
ORDER = inCfg['PATH']['OUT']['ORDER']  # 读取目录信息
MVREC = inCfg['PATH']['OUT']['MVREC']
T_DATA = inCfg['PATH']['OUT']['T_DATA']

# 判断系统的类型
if 'nt' in os.name:
    OSTYPE = 'windows'
elif 'posix' in os.name:
    OSTYPE = 'linux'
else:
    Log.info(u'不识别的系统类型')
    sys.exit(-1)

# 开始sock服务，判断该端口是否被占用。如果占用则退出
port = 9802
sserver = SocketServer()
if sserver.createSocket(port) == False:
    Log.info(u'----已经有一个实例在实行')
    sys.exit(-1)

# 获取开机线程的个数，开启线程池。获取订单对时间和编号进行并行操作
threadNum = inCfg['TOOL']['thread']
pool = threadpool.ThreadPool(int(threadNum))

# 手动执行跟2个参数，卫星明和时间段
if len(args) == 2:
    Log.info(u'手动数据下载程序开始运行-----------------------------')

    satID = args[0]  # 卫星全名
    str_time = args[1]  # 程序执行时间范围

    # 进行时间的解析，由YYYYMMDD-YYYYMMDD 转为datetime类型的开始时间和结束时间
    date_s, date_e = pb_time.arg_str2date(str_time)

    while date_s <= date_e:
        # 时间转换
        ymd = date_s.strftime('%Y%m%d')
        date_s = date_s + relativedelta(days=1)
        MODE_D = inCfg['ORDER'][satID]['MODE_D']
        # 判断下载开关是否打开
        if 'ON' in MODE_D:
            run(satID, ymd)

elif len(args) == 0:
    Log.info(u'自动数据下载程序开始运行-----------------------------')

    rolldays = inCfg['CROND']['rolldays']
    satLst = inCfg['ORDER'].keys()
    for satID in satLst:
        MODE_D = inCfg['ORDER'][satID]['MODE_D']
        # 判断下载开关是否打开
        if 'ON' not in MODE_D:
            continue
        for rdays in rolldays:
            ymd = (datetime.utcnow() - relativedelta(days=int(rdays))).strftime('%Y%m%d')
            run(satID, ymd)
else:
    print 'args: satName yyyymmdd-yyyymmdd or args: NULL'
    sys.exit(-1)
