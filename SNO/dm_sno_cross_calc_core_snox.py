# coding:UTF-8
'''
Created on 2015年10月13日

@author: 弢@kingtansin
'''
import os, sys
import numpy as np
from PB.pb_time import ymd_plus, get_local_time
from PB.pb_space import distance_GreatCircle, distance_GreatCircle_np, solar_zen
from dm_sno_cross_calc_map import draw_fixed, draw_polar, draw_world, draw_china
import warnings
from shapely.geometry import LineString
reload(sys) 
sys.setdefaultencoding('utf8')

def load_orbit(orbitPath):
    '''
    载入卫星轨迹文件
    orbitPath： 卫星轨迹文件全路径
    '''
    orbit = np.loadtxt(orbitPath,
                       dtype={'names': ('date', 'time', 'Lat', 'Lon'),
                              'formats': ('S10', 'S8', 'f4', 'f4')},
                       skiprows=6, ndmin=2)  # 跳过头6行
    return orbit
    
class Sat_Orbit(object):
    '''
    卫星轨迹类
    '''

    def __init__(self, sat, ymd, ORBIT_ROOT, Log=None):
        '''
        Constructor
        '''
        self.sat = sat
        self.ymd = str(ymd)
        self.orbit_14days = []
        self.orbitDir = ''
        self.orbit = []
        self.divide = []
        self.lonE = None
        self.lonW = None
        self.latN = None
        self.latS = None
        self.error = False
        self.__getOrbitDir(ORBIT_ROOT)
#         20160708 黄叶建huangyj modify
#        该程序将不再产生log记录
        self.Log = Log
        
    def clear(self):
        self.orbit = []
        self.divide = []
        self.lonE = None
        self.lonW = None
        self.latN = None
        self.latS = None
        self.error = False
#     20160708 黄叶建  huangyj modify
#     def Log_error(self, strError):
#         if self.Log is not None:
#             self.Log.error(strError)
    
    def __getOrbitDir(self, ORBIT_ROOT):
        '''
        找对应卫星的轨迹文件若在目录
        '''
        self.orbitDir = os.path.join(ORBIT_ROOT, self.sat)
        if not os.path.isdir(self.orbitDir):
#             20160708 黄叶建haungyj modify
#             self.Log_error("No such sat: %s in %s" % (self.sat, ORBIT_ROOT))
            self.error = True
            return

#         date_s = ymd2date(self.ymd)
#         for iday in range(7):  #  没有当日的则往前找，最多往前找7天
#             ymd = (date_s - relativedelta(days=iday)).strftime('%Y%m%d')
#             txtPath = os.path.join(orbitDir, '%s.txt' % ymd)
#             if os.path.isfile(txtPath):
#                 self.orbitPath = txtPath
#                 return
# 
#         self.error = True

    def setArea(self, latlonInfo):
        self.latN, self.latS, self.lonW, self.lonE = [float(each) for each in latlonInfo]
        if (-90. <= self.latN <= 90. and -90. <= self.latS <= 90. and
        
            
            -180. <= self.lonW <= 180. and -180. <= self.lonE <= 180. and
            self.latN >= self.latS and self.lonW < self.lonE):
            pass
        else:

            pass
        
            
            self.Log.error("Worng Area: N %.2f S %.2f W %.2f E %.2f" % 
                    (self.latN, self.latS, self.lonW, self.lonE))
            self.error = True
    
    def get_orbit(self, ymd):
        self.clear()
        if len(ymd) != 8:
            raise Exception("Wrong YMD %s" % ymd) 
        else:
            txtPath = os.path.join(self.orbitDir, '%s.txt' % ymd)
            if os.path.isfile(txtPath):
                orbit = load_orbit(txtPath)
                self.orbit = orbit[np.where(orbit['date'] == ymd2y_m_d(ymd))]
#         20160708 黄叶建huangyj modify
        if len(self.orbit) == 0:
            self.Log.error("%s no orbit %s" % (self.sat, ymd))
            self.error = True

    def divide_by_lat_lon(self):
        '''
        将一天的轨迹过 latN 和 latS 线的点的index存入list
        '''
        if self.latN == self.latS:
            # 极地情况
            if self.latN >= 0:  # 北半球
                condition = np.logical_and(self.orbit['Lat'] > self.latN, self.orbit['Lon'] < self.lonE)
                condition = np.logical_and(condition, self.orbit['Lon'] > self.lonW)
            else:  # 南半球
                condition = np.logical_and(self.orbit['Lat'] < self.latN, self.orbit['Lon'] < self.lonE)
                condition = np.logical_and(condition, self.orbit['Lon'] > self.lonW)
        else:
            condition = np.logical_and(self.orbit['Lat'] < self.latN, self.orbit['Lon'] < self.lonE)
            condition = np.logical_and(condition, self.orbit['Lat'] > self.latS)
            condition = np.logical_and(condition, self.orbit['Lon'] > self.lonW)

        y_cross = np.where(np.diff(condition) > 0)[0] + 1
        self.divide.extend(y_cross)
        
        self.divide.sort()  # 排序
        i_old = -999
        index_lst = []
        for i in self.divide:
            if (i - i_old > 5):  # 去掉秒数在5秒以内的浮动点
                index_lst.append(i)
            i_old = i
        self.divide = index_lst
        
    def divide_orbit(self):
        '''
        将轨迹分段，便于计算
        '''
        self.__divide_by_lat_UpAndDown()
        self.__divide_by_lon180()
        
        self.divide.sort()
        if self.divide[0] != 0:
            self.divide.insert(0, 0)
        self.divide.append(len(self.orbit['Lat']))
           
    def __divide_by_lat_UpAndDown(self):
        '''
        将一天的轨迹分成升降轨的不同段，将分割点的index存入list
        '''
        y_growth_flips = np.where(np.diff(np.diff(self.orbit['Lat']) > 0))[0] + 1
        
        i_old = 0
        index_lst = [] 
        for i in y_growth_flips:
            if (i - i_old > 60):  # 同时去掉秒数在60秒以内的浮动点
                index_lst.append(i)
            i_old = i
        
        self.divide.extend(index_lst)

    def __divide_by_lon180(self):
        '''
        将一天的轨迹根据lon180，将分割点的index存入list
        '''
        x_growth_jumps = np.where(np.diff(self.orbit['Lon']) > 180.)[0] + 1
        self.divide.extend(x_growth_jumps)

    def divide_by_lat0(self):
        '''
        将一天的轨迹根据赤道，将分割点的index存入list
        '''
        y_cross = np.where(np.diff((self.orbit['Lat'] < 0.).astype('int')))[0] + 1
        self.divide.extend(y_cross)
        self.divide.sort()
        
def ymd2y_m_d(ymd, split='.'):
    if len(ymd) != 8:
        return None
    return split.join([ymd[:4], ymd[4:6], ymd[6:]])
        
def runSatPassingArea(s1, areaName, latlonInfo, outPath, Log):
    '''
    s1 : Sat_Orbit的实例
    areaName: 区域名称
    latlonInfo: list,区域上下左右4个经纬度
    outPath： 输出全路径
    '''
    index_list = []

    s1.get_orbit(s1.ymd)  # 只计算一天
    if s1.error:
        return
    s1.setArea(latlonInfo)
    if s1.error:
        return

    latN, latS, lonW, lonE = latlonInfo
    if latN == '90' and latS == '-90' and lonW == '-180' and lonE == '180':
        index_list = [[0, len(s1.orbit) - 1]]

    else:
        s1.divide_by_lat_lon()  # 轨迹分段

        index_pair = []
         
        for j in s1.divide:
            if j <= 5: continue
            if j >= len(s1.orbit['Lon']) - 6: continue

            j1 = j - 5
            j2 = j + 5

            if latN == latS:  # 极地情况
                if latN >= 0:  # 北半球
                    # 入区域
                    if (s1.lonW <= s1.orbit['Lon'][j2] <= s1.lonE and
                        s1.latN <= s1.orbit['Lat'][j2] and
                            (s1.lonE < s1.orbit['Lon'][j1] or s1.orbit['Lon'][j1] < s1.lonW or
                             s1.latN > s1.orbit['Lat'][j1])):
                        index_pair = []
                        index_pair.append(j)
        
                    # 出区域
                    elif (s1.lonW <= s1.orbit['Lon'][j1] <= s1.lonE and
                          s1.latN <= s1.orbit['Lat'][j1] and
                              (s1.lonE < s1.orbit['Lon'][j2] or s1.orbit['Lon'][j2] < s1.lonW or
                               s1.latN > s1.orbit['Lat'][j2])):
                        index_pair.append(j)
                        if len(index_pair) == 2:
                            index_list.append(index_pair)
                        index_pair = []
                else:  # 南半球
                    # 入区域
                    if (s1.lonW <= s1.orbit['Lon'][j2] <= s1.lonE and
                        s1.latN >= s1.orbit['Lat'][j2] and
                            (s1.lonE < s1.orbit['Lon'][j1] or s1.orbit['Lon'][j1] < s1.lonW or
                             s1.latN < s1.orbit['Lat'][j1])):
                        index_pair = []
                        index_pair.append(j)
        
                    # 出区域
                    elif (s1.lonW <= s1.orbit['Lon'][j1] <= s1.lonE and
                          s1.latN >= s1.orbit['Lat'][j1] and
                              (s1.lonE < s1.orbit['Lon'][j2] or s1.orbit['Lon'][j2] < s1.lonW or
                               s1.latN < s1.orbit['Lat'][j2])):
                        index_pair.append(j)
                        if len(index_pair) == 2:
                            index_list.append(index_pair)
                        index_pair = []                     
            else:
                # 入区域
                if (s1.lonW <= s1.orbit['Lon'][j2] <= s1.lonE and
                    s1.latS <= s1.orbit['Lat'][j2] <= s1.latN and
                        (s1.lonE < s1.orbit['Lon'][j1] or s1.orbit['Lon'][j1] < s1.lonW or
                         s1.latN < s1.orbit['Lat'][j1] or s1.orbit['Lat'][j1] < s1.latN)):
                    index_pair = []
                    index_pair.append(j)
    
                # 出区域
                elif (s1.lonW <= s1.orbit['Lon'][j1] <= s1.lonE and
                      s1.latS <= s1.orbit['Lat'][j1] <= s1.latN and
                          (s1.lonE < s1.orbit['Lon'][j2] or s1.orbit['Lon'][j2] < s1.lonW or
                           s1.latN < s1.orbit['Lat'][j2] or s1.orbit['Lat'][j2] < s1.latN)):
                    index_pair.append(j)
                    if len(index_pair) == 2:
                        index_list.append(index_pair)
                    index_pair = []

    if len(index_list) == 0:
        Log.info('Not Passing Area!')
        return

    folder = os.path.dirname(outPath)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    fp = open(outPath, 'w')
    # 写十行信息
    fp.write('Sat: %s\n' % s1.sat)
    fp.write('Area: %s\n' % areaName)
    fp.write('Time: %s \n' % ymd2y_m_d(s1.ymd))
    fp.write('latlonInfo:\n')
    fp.write('  lat N: %.4f    lat S: %.4f\n' % (s1.latN, s1.latS))
    fp.write('  lon W: %.4f    lon E: %.4f\n' % (s1.lonW, s1.lonE))
    fp.write('Calc time : %s \n' % get_local_time().strftime('%Y.%m.%d %H:%M:%S'))
    fp.write('\n')
    title_line = 'YMD       HMS(start)  HMS(end)    Lat,Lon(start)    Lat,Lon(end)\n'
    fp.write(title_line)
    fp.write('-' * len(title_line) + '\n')
    #
    for eachPair in index_list:
        i1, i2 = eachPair
        fp.write('%s  %s    %s    %6.2f  %-7.2f  %6.2f  %-7.2f\n' % 
                 (s1.ymd, s1.orbit['time'][i1][0:8], s1.orbit['time'][i2][0:8],
                  s1.orbit['Lat'][i1], s1.orbit['Lon'][i1],
                  s1.orbit['Lat'][i2], s1.orbit['Lon'][i2]))
    fp.close()
    # clean
    s1.clear()
    Log.info('Success')

def runSatPassingFixedPoint(s1, fix_list, fix_dist, outPath, FIX_DICT, Log, day_counts=1):
    '''
    s1 : Sat_Orbit的实例
    fix_list: 固定点组名list
    fix_dist: 距离阈值
    outPath： 输出txt全路径
    day_counts： 算几天
    '''
    out_fig = outPath.replace('.txt', '.png')
    
    fixDict = {}
    drew_points = []
    output_list = []
    
    # 去重
    for fix_group in fix_list:  # 循环不同组
        for fix_point in FIX_DICT[fix_group].keys():  # 循环每个组中的键
            if fix_point not in fixDict.keys():  # 如果键不存在字典中，则将该键和键值进行存入
                fixDict[fix_point] = FIX_DICT[fix_group][fix_point]
            
    for fix_point in fixDict.keys():
        fixed_lon, fixed_lat = [float(e) for e in fixDict[fix_point]]  # 提取站点的经度和维度

        #   log.debug('%s and %s of %s' % (fixed_point[0], sat2, date))   
        for day_num in range(0, day_counts):  
            ymd = ymd_plus(s1.ymd, day_num)  # 将进行进行进行往后推
            
            s1.get_orbit(ymd)
            if s1.error:        continue
            if len(s1.orbit) == 0: continue
            
            l = len(s1.orbit)
            lat_fixed_array = np.array([fixed_lat] * l)
            lon_fixed_array = np.array([fixed_lon] * l)            

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")  # Suppressing RuntimeWarning
                deltaDist_list = distance_GreatCircle_np(lat_fixed_array,
                                                    lon_fixed_array,
                                                    s1.orbit['Lat'],
                                                    s1.orbit['Lon'])
                y_growth_flips = np.where(np.diff(np.diff(deltaDist_list) > 0))[0] + 1

            i_old = 0
            cross_list = []
            for i in y_growth_flips:
                if (deltaDist_list[i] < fix_dist and 
                    (i - i_old > 10) and  # 去掉间隔秒数在10秒以内的点
                    (deltaDist_list[i] - deltaDist_list[i_old] < 0)):  
                    cross_list.append((i, deltaDist_list[i]))  # 每行2个元素：index, deltaDist_list
                i_old = i

            # 排序 按deltaDist从小到大
            cross_list.sort(cmp_byDeltaDist)
            if(len(cross_list) == 0):
                continue
            
            j = 0
            for each in cross_list:
                cross_index = each[0]

                # TODO:过滤夜晚数据 -------------------
                # 以太阳天顶角 大于85度作为夜晚的判断。  
                # 用这种方法，'Greenland' 'Dome_C'就不需要特别考虑极夜极昼了
                ymd_sol = s1.orbit['date'][cross_index]
                yy = int(ymd_sol[:4])
                mm = int(ymd_sol[5:7])
                dd = int(ymd_sol[8:10])
                hh = int(s1.orbit['time'][cross_index][0:2])
                if solar_zen(yy, mm, dd, hh, s1.orbit['Lon'][cross_index], s1.orbit['Lat'][cross_index]) >= 85.:
                    continue
                # ------------------------------
                                   
                output_list.append([s1.orbit['date'][cross_index].replace('.', ''), \
                                    s1.orbit['time'][cross_index][0:8], \
                                    fix_point, fixed_lat, fixed_lon, \
                                    s1.orbit['Lat'][cross_index], s1.orbit['Lon'][cross_index], \
                                    deltaDist_list[cross_index]])
    
                # 保留画图信息                   
                st = max(cross_index - 240, 0)
                et = min(cross_index + 80, len(s1.orbit['Lon']))
                drew_points.append((fixed_lon, fixed_lat,
                                    s1.orbit['Lon'][cross_index], s1.orbit['Lat'][cross_index],
                                    [None, None],
                                    [s1.orbit['Lon'][st : et], s1.orbit['Lat'][st : et]]))
                
                j = j + 1
                if fix_point in ['Greenland', 'Dome_C']:
                    pass  # 冰雪目标全部保留
                elif j >= 1:  # 其他目标只保留最近点
                    break

    if(len(output_list) == 0):
        Log.info('No SNO!')
        return

    # 排序
    output_list.sort(cmp_col0_col1)   

    ymd_s = ymd2y_m_d(s1.ymd)
    
    # 画图
    if len(drew_points) > 0:
        draw_fixed(s1.sat, ymd_s, ymd2y_m_d(ymd), drew_points, out_fig)

    folder = os.path.dirname(outPath)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    # 写文件
    fid_Result = open(outPath, 'w')
    fid_Result.write('Sat: %s \n' % s1.sat)
    if ymd_s == ymd : 
        fid_Result.write('Time: %s \n' % ymd_s)
    else:
        fid_Result.write('Time: %s-%s \n' % (ymd_s, ymd))
    fid_Result.write('Dist MAX = %s (km) \n' % fix_dist)
    fid_Result.write(u'Solar Zenith MAX = 85° \n')
    fid_Result.write(u'    对于Greenland和Dome_C，保留所有符合阈值的每轨最近点\n')
    fid_Result.write(u'    对于其它固定点，只保留符合阈值的全天最近点\n')
    fid_Result.write('Calc time : %s \n' % get_local_time().strftime('%Y.%m.%d %H:%M:%S'))
    fid_Result.write('\n')
    title_line = 'YMD     HMS(%s)    %-24s %-16s %-19s %s \n' % \
                 (s1.sat, 'Fixed_Point', 'Lat,Lon(Fixed)', 'Lat,Lon(%s)' % s1.sat, 'Distance(km)')

    fid_Result.write(title_line)
    fid_Result.write('-' * len(title_line) + '\n')
    for eachline in output_list:

        fid_Result.write('%s    %s       %-24s %6.2f  %-7.2f     %6.2f  %-7.2f   %7.2f\n' % \
                         tuple(eachline))

    fid_Result.close()
    # clean
    s1.clear()
    Log.info('Success')
    
def cmp_col0_col1(x, y):
    '''
    排序固定点输出列表
    比较第一列, 第二列
    '''
    if x[0] == y[0]:
        return cmp(x[1], y[1])
    else:
        return cmp(x[0], y[0])
    
def cmp_byDeltaDist(x, y):
    return cmp(x[1], y[1])

def runLEO_LEO(s1, s2, sat_dist, timeGap_high, timeGap_low, outPath, Log, day_counts=1):
    '''
    极轨对极轨 交叉点计算
    '''
    drew_points = []
    output_list = []
    for day_num in range(0, day_counts):  
        ymd = ymd_plus(s1.ymd, day_num)
        
        s1.get_orbit(ymd)
        if s1.error:        continue
        s2.get_orbit(ymd)
        if s2.error:        continue
        if len(s1.orbit) == 0 or len(s2.orbit) == 0:
            continue
        s1.divide_orbit()
        s2.divide_orbit()
        
        day_list = []  # 输出用
#         day_points = []  # 画图用
        for i in xrange(len(s1.divide)):
            if i == 0 : continue
    
            ii_s = s1.divide[i - 1]
            ii_e = s1.divide[i]
            if abs(ii_e - ii_s) < 2:
                continue
            
            line1 = LineString(zip(s1.orbit['Lon'][ii_s:ii_e],
                                   s1.orbit['Lat'][ii_s:ii_e]))
            for j in xrange(len(s2.divide)):
                if j == 0 : continue
                jj_s = s2.divide[j - 1]
                jj_e = s2.divide[j]
                if abs(jj_e - jj_s) < 2:
                    continue
                                        
                if abs(ii_s + ii_e - jj_s - jj_e) > timeGap_low * 60 * 2 * 4:  # 中间点4倍时间范围粗筛
                    continue
                
                line2 = LineString(zip(s2.orbit['Lon'][jj_s:jj_e],
                                       s2.orbit['Lat'][jj_s:jj_e]))
                
                inters = line1.intersection(line2)
                if inters.geom_type == 'Point':
                    pass
                elif inters.geom_type == 'MultiPoint':
                    inters = np.array(inters)
                    if (np.abs(np.diff(inters[:, 0])) < 1.).all() and \
                       (np.abs(np.diff(inters[:, 1])) < 1.).all():
                        inters = [np.mean(inters[:, 0]), np.mean(inters[:, 1])]
                    else:
                        continue
                else:
                    continue
                
                inters = np.array(inters)  # 转成array
                
                if len(inters) > 0:
                    index1 = ii_s + getIndex(s1.orbit['Lon'][ii_s:ii_e], inters[0])
                    index2 = jj_s + getIndex(s2.orbit['Lon'][jj_s:jj_e], inters[0])
                    
                    timeDiff = index2 - index1

                    if abs(timeDiff) <= timeGap_low * 60:
                        # 60度以上高纬 timeGap过滤
                        if abs(s1.orbit['Lat'][index1]) > 60. and \
                           abs(timeDiff) > timeGap_high * 60:
                            continue
                        
                        dd = distance_GreatCircle(s1.orbit['Lat'][index1],
                                                  s1.orbit['Lon'][index1],
                                                  s2.orbit['Lat'][index2],
                                                  s2.orbit['Lon'][index2])
                        if dd > sat_dist:
                            continue
                        day_list.append([s1.orbit['date'][index1].replace('.', ''),
                                         s1.orbit['time'][index1][0:8],
                                         s1.orbit['Lat'][index1], s1.orbit['Lon'][index1],
                                         s2.orbit['time'][index2][0:8],
                                         s2.orbit['Lat'][index2], s2.orbit['Lon'][index2],
                                         dd, timeDiff])
                        
                        # 画图所需信息
                        st = max(index1 - 240, 0)
                        et = min(index1 + 80, len(s1.orbit['Lon']))
                        trails1 = [s1.orbit['Lon'][st : et], s1.orbit['Lat'][st : et]]
                        st = max(index2 - 240, 0)
                        et = min(index2 + 80, len(s2.orbit['Lon']))
                        trails2 = [s2.orbit['Lon'][st : et], s2.orbit['Lat'][st : et]]
                        
                        drew_points.append((s1.orbit['Lon'][index1], s1.orbit['Lat'][index1],
                                            s2.orbit['Lon'][index2], s2.orbit['Lat'][index2],
                                            trails1,
                                            trails2))
                    
        # ------- 交叉点多  隔3个 取一个 --------
        output_list.extend(day_list[::3])
#         drew_points.extend(day_points[::3])
        # -----------------------
    if len(output_list) == 0:
#         20160708 黄叶建huangyj modify
        Log.info('No SNO!')
        return
    
    pout_fig_file = outPath.replace('.txt', '_polarmap.png')
    wout_fig_file = outPath.replace('.txt', '_worldmap.png')
    
    ymd_s = ymd2y_m_d(s1.ymd)
    
    # 画交叉点图像
    if len(drew_points) > 0:
        draw_polar(s1.sat, s2.sat, ymd_s, ymd2y_m_d(ymd), drew_points, pout_fig_file)
        draw_world(s1.sat, s2.sat, ymd_s, ymd2y_m_d(ymd), drew_points, wout_fig_file)

    folder = os.path.dirname(outPath)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    # 输出交叉点文件
    fid_Result = open(outPath, 'w')
    fid_Result.write('Sat1: %s \n' % (s1.sat))
    fid_Result.write('Sat2: %s \n' % (s2.sat))
    if ymd_s == ymd:
        fid_Result.write('Time: %s \n' % ymd_s)
    else:
        fid_Result.write('Time: %s-%s \n' % (ymd_s, ymd))
    fid_Result.write('When |lat|<=60: Time Gap MAX = %d min\n' % timeGap_low)
    fid_Result.write('When |lat|>60:  Time Gap MAX = %d min\n' % timeGap_high)
    fid_Result.write('Dist MAX = %d (km)\n' % sat_dist)
    fid_Result.write('Calc time : %s \n' % get_local_time().strftime('%Y.%m.%d %H:%M:%S'))
    fid_Result.write('\n')
    title_line = 'YMD    HMS(%s)  Lat,Lon(%s)    HMS(%s)    Lat,Lon(%s)    Distance(km)   Time_Diff(sec)\n' % \
                 (s1.sat, s1.sat, s2.sat, s2.sat)
    fid_Result.write(title_line)
    fid_Result.write('-' * len(title_line) + '\n')
    
    for eachline in output_list:
        fid_Result.write('%s     %s      %6.2f  %-7.2f     %s      %6.2f  %-7.2f   %7.2f           %4d\n' % \
                         tuple(eachline))
    fid_Result.close()
    s1.clear()

    Log.info('Success')

def getIndex(lonlist, lon):
    lon_dist = lonlist - lon
    tmp = np.ma.masked_less_equal(lon_dist, 0)
    i1 = np.argmin(tmp)
    tmp = np.ma.masked_greater_equal(lon_dist, 0)
    i2 = np.argmax(tmp)
    return min(i1, i2)

def runGEO_LEO(s1, s2, sat_dist, outPath, Log):
    '''
    # 和过区域算法一样
    s1 : Sat_Orbit的实例  LEO
    s2 : Sat_Orbit的实例  GEO
    latlonInfo: list,区域上下左右4个经纬度
    outPath： 输出全路径
    '''
    
    s1.get_orbit(s1.ymd)  # 只计算一天
    if s1.error:
        return
    s2.get_orbit(s1.ymd)
    if s2.error:
        return    
    lat0 = s2.orbit['Lat'][0]
    lon0 = s2.orbit['Lon'][0]
    latlonInfo = [lat0 + sat_dist, lat0 - sat_dist, lon0 - sat_dist, lon0 + sat_dist]
    s1.setArea(latlonInfo)
    if s1.error:
        return

    s1.divide_by_lat_lon()  # 轨迹分段
    
    index_list = []
    index_pair = []
    for j in s1.divide:
        if j <= 5: continue
        if j >= len(s1.orbit['Lon']) - 6: continue

        j1 = j - 5
        j2 = j + 5

        # 入区域
        if (s1.lonW <= s1.orbit['Lon'][j2] <= s1.lonE and
                        s1.latS <= s1.orbit['Lat'][j2] <= s1.latN and
                (s1.lonE < s1.orbit['Lon'][j1] or s1.orbit['Lon'][j1] < s1.lonW or
                         s1.latN < s1.orbit['Lat'][j1] or s1.orbit['Lat'][j1] < s1.latN)):
            index_pair = []
            index_pair.append(j)

        # 出区域
        elif (s1.lonW <= s1.orbit['Lon'][j1] <= s1.lonE and
                          s1.latS <= s1.orbit['Lat'][j1] <= s1.latN and
                  (s1.lonE < s1.orbit['Lon'][j2] or s1.orbit['Lon'][j2] < s1.lonW or
                           s1.latN < s1.orbit['Lat'][j2] or s1.orbit['Lat'][j2] < s1.latN)):
            index_pair.append(j)
            if len(index_pair) == 2:
                index_list.append(index_pair)
            index_pair = []

    if len(index_list) == 0:
        Log.info('Not Passing Area!')
        return

    # 画图    sat2(GEO) 在前
    out_fig = outPath.replace('.txt', '_worldmap.png')
    drew_points = []
    for i1, i2 in index_list:
        trails1 = [s1.orbit['Lon'][i1 : i2], s1.orbit['Lat'][i1 : i2]]
        trails2 = [None, None]
        drew_points.append((None, None,
                            None, None,
                            trails2,
                            trails1))
    if len(drew_points) > 0:
        drew_points.append((lon0, lat0,
                            None, None,
                            [None, None],
                            [None, None]))
    if len(drew_points) > 0:
        draw_china(s2.sat, s1.sat, ymd2y_m_d(s1.ymd), ymd2y_m_d(s1.ymd),
                   drew_points, out_fig)
        
    folder = os.path.dirname(outPath)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    fp = open(outPath, 'w')
    # 写十行信息
    fp.write(u'GEO: %s    (星下点  lat = %.2f, lon = %.2f)\n' % (s2.sat, lat0, lon0))
    fp.write('LEO: %s\n' % s1.sat)
    fp.write('Time: %s\n' % ymd2y_m_d(s1.ymd))
    fp.write('latlonInfo:  Square side 1/2 = %s (degree)\n' % sat_dist)
    fp.write('  lat N: %.4f    lat S: %.4f\n' % (s1.latN, s1.latS))
    fp.write('  lon W: %.4f    lon E: %.4f\n' % (s1.lonW, s1.lonE))
    fp.write('Calc time : %s \n' % get_local_time().strftime('%Y.%m.%d %H:%M:%S'))
    fp.write('\n')
    title_line = 'YMD       HMS(start)  HMS(end)    Lat,Lon(start)    Lat,Lon(end)\n'
    fp.write(title_line)
    fp.write('-' * len(title_line) + '\n')
    #
    for eachPair in index_list:
        i1, i2 = eachPair
        fp.write('%s  %s    %s    %6.2f  %-7.2f  %6.2f  %-7.2f\n' % 
                 (s1.ymd, s1.orbit['time'][i1][0:8], s1.orbit['time'][i2][0:8],
                  s1.orbit['Lat'][i1], s1.orbit['Lon'][i1],
                  s1.orbit['Lat'][i2], s1.orbit['Lon'][i2]))
    fp.close()
    # clean
    s1.clear()    
    Log.info('Success')

def runLEO_LEO_SNOX(s1, s2, sat_dist, timeGap, outPath, Log, day_counts=1):
    '''
    极轨对极轨 交叉点计算
    '''
    drew_points = []
    output_list = []
    for day_num in range(0, day_counts):  
        ymd = ymd_plus(s1.ymd, day_num)
        
        s1.get_orbit(ymd)
        if s1.error:        continue
        s2.get_orbit(ymd)
        if s2.error:        continue
        if len(s1.orbit) == 0 or len(s2.orbit) == 0:
            continue
        s1.divide_by_lat0()
        s2.divide_by_lat0()
        
        day_list = []  # 输出用
        for i in xrange(len(s1.divide)):           
            index1 = s1.divide[i]
            for j in xrange(len(s2.divide)):
                index2 = s2.divide[j]
                timeDiff = index2 - index1 
                if abs(timeDiff) > timeGap * 60:
                    continue
                
                dist = distance_GreatCircle(s1.orbit['Lat'][index1],
                                          s1.orbit['Lon'][index1],
                                          s2.orbit['Lat'][index2],
                                          s2.orbit['Lon'][index2])
                if dist > sat_dist:
                    continue
                
                # TODO: 只保留太阳天顶角<80°的点（白天)
                yy, mm, dd = s1.orbit['date'][index1].split(".")
                hh = int(s1.orbit['time'][index1][0:2])
                sz = solar_zen(yy, mm, dd, hh, s1.orbit['Lon'][index1], s1.orbit['Lat'][index1])
                if sz > 80:
                    continue
                
                day_list.append([s1.orbit['date'][index1].replace('.', ''),
                                 s1.orbit['time'][index1][0:8],
                                 s1.orbit['Lat'][index1], s1.orbit['Lon'][index1],
                                 s2.orbit['time'][index2][0:8],
                                 s2.orbit['Lat'][index2], s2.orbit['Lon'][index2],
                                 dist, timeDiff])
                        
                # 画图所需信息
                st = max(index1 - 240, 0)
                et = min(index1 + 80, len(s1.orbit['Lon']))
                trails1 = [s1.orbit['Lon'][st : et], s1.orbit['Lat'][st : et]]
                st = max(index2 - 240, 0)
                et = min(index2 + 80, len(s2.orbit['Lon']))
                trails2 = [s2.orbit['Lon'][st : et], s2.orbit['Lat'][st : et]]
                
                drew_points.append((s1.orbit['Lon'][index1], s1.orbit['Lat'][index1],
                                    s2.orbit['Lon'][index2], s2.orbit['Lat'][index2],
                                    trails1,
                                    trails2))
                
        output_list.extend(day_list)            
    # -----------------------
    if len(output_list) == 0:
        Log.info('No SNOX!')
        return
    
    wout_fig_file = outPath.replace('.txt', '_worldmap.png')
    
    ymd_s = ymd2y_m_d(s1.ymd)
    
    # 画交叉点图像
    if len(drew_points) > 0:
        draw_world(s1.sat, s2.sat, ymd_s, ymd2y_m_d(ymd), drew_points, wout_fig_file)

    folder = os.path.dirname(outPath)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    # 输出交叉点文件
    fid_Result = open(outPath, 'w')
    # 写十行信息
    fid_Result.write('Sat1: %s \n' % (s1.sat))
    fid_Result.write('Sat2: %s \n' % (s2.sat))
    if ymd_s == ymd:
        fid_Result.write('Time: %s \n' % ymd_s)
    else:
        fid_Result.write('Time: %s-%s \n' % (ymd_s, ymd))
    fid_Result.write('Time Gap MAX = %d min\n' % timeGap)
    fid_Result.write('Dist MAX = %d (km)\n' % sat_dist)
    fid_Result.write('Solar Zenith MAX = 80 (deg)\n')
    fid_Result.write('Calc time : %s \n' % get_local_time().strftime('%Y.%m.%d %H:%M:%S'))
    fid_Result.write('\n')
    title_line = 'YMD      HMS(%s)      Lat,Lon(%s)      HMS(%s)      Lat,Lon(%s)      Distance(km)      Time_Diff(sec)\n' % \
                 (s1.sat, s1.sat, s2.sat, s2.sat)
    fid_Result.write(title_line)
    fid_Result.write('-' * len(title_line) + '\n')
    
    for eachline in output_list:
        fid_Result.write('%s     %s      %6.2f  %-7.2f     %s      %6.2f  %-7.2f   %7.2f           %4d\n' % \
                         tuple(eachline))
    fid_Result.close()
    s1.clear()

    Log.info('Success')
       
if __name__ == '__main__':
    pass
#     print FIX_DICT['group1'].as_float('qinghaihu')
