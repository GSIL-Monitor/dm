# coding=UTF-8
__author__ = 'wangpeng'

'''
按顺序进行调度作业
1、报文下载
2、轨迹计算
3、交叉预报

'''
import os

MainPath, SnoFile = os.path.split(os.path.realpath(__file__))
def main():
    os.system('python27 %s ' % os.path.join(MainPath, 'dm_sno_title_down.pyc'))
    os.system('python27 %s ' % os.path.join(MainPath, 'dm_sno_orbit_calc.pyc'))
    os.system('python27 %s ' % os.path.join(MainPath, 'dm_sno_cross_calc.pyc'))

if __name__ == '__main__':
    main()
