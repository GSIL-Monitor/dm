# coding:UTF-8
'''
Created on 2013年11月14日
在地图上标注轨迹，交叉点，最近点

@author: zhangtao
'''
import os
import matplotlib as mpl
mpl.use('Agg')
import numpy as np
from DV.dv_pub_legacy import FONT0
from mpl_toolkits.basemap import Basemap
import matplotlib.patches as mpatches
from pylab import plt, subplot
from matplotlib.collections import LineCollection

# mpl全局参数设定
# mpl.rcParams['font.size'] = 6
MainPath = os.path.dirname(__file__)
plt.style.use(os.path.join(MainPath, 'dm_sno.mplstyle'))

ORG_NAME = 'NSMC-GPRC'

LINE_WIDTH = 0.5
EDGE_GRAY = '#303030'

# palette 1
RED = '#f63240'
BLUE = '#1c56fb'
GRAY = '#c0c0c0'

# print FONT0.get_size()
TICKER_FONT = FONT0.copy()
TICKER_FONT.set_size(11)

def draw_satTrail(lons, lats, color, Trail_Width=1):
    '''
    画卫星轨迹
    '''
    lons_tmp = []
    lats_tmp = []
    lon_old = lons[0]
    for i in xrange(len(lons)):
        if abs(lons[i] - lon_old) >= 180.:  # 轨迹每次过精度180，就分割画一次
            plt.plot(lons_tmp, lats_tmp, '-', linewidth=Trail_Width, c=color)
            lons_tmp = []
            lats_tmp = []
            
        lon_old = lons[i]
        lons_tmp.append(lons[i])
        lats_tmp.append(lats[i])

    plt.plot(lons_tmp, lats_tmp, '-', linewidth=Trail_Width, c=color)

def draw_satTrail_multicolor(lons, lats, colormap, Trail_Width=1):
    '''
    画卫星轨迹，根据colormap使颜色渐变
    '''
    t = np.linspace(0, len(lons), len(lons))

    lons_tmp = []
    lats_tmp = []
    lon_old = lons[0]
    ti = 0
    for i in xrange(len(lons)):
        if abs(lons[i] - lon_old) >= 180.:  # 轨迹每次过精度180，就分割画一次
            points = np.array([lons_tmp, lats_tmp]).T.reshape(-1, 1, 2)
            segments = np.concatenate([points[:-1], points[1:]], axis=1)
        
            lc = LineCollection(segments, cmap=plt.get_cmap(colormap),  # YlGnBu
                                norm=plt.Normalize(0, len(lons)))
            lc.set_array(t[ti:i])
            lc.set_linewidth(Trail_Width)
            plt.gca().add_collection(lc)
#             plt.plot(lons_tmp, lats_tmp, '-', linewidth=Trail_Width, c=color)
            lons_tmp = []
            lats_tmp = []
            ti = i
            
        lon_old = lons[i]
        lons_tmp.append(lons[i])
        lats_tmp.append(lats[i])

#     plt.plot(lons_tmp, lats_tmp, '-', linewidth=Trail_Width, c=color)
    points = np.array([lons_tmp, lats_tmp]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    lc = LineCollection(segments, cmap=plt.get_cmap(colormap),  # YlGnBu
                        norm=plt.Normalize(0, len(lons)))
    lc.set_array(t[ti:i])
    lc.set_linewidth(Trail_Width)
    plt.gca().add_collection(lc)

def draw_closestPoints(m, closestPointsList, date, color_sat1, color_sat2):
    '''
    画最近点
    '''
    list1 = [[each[2], each[3], each[4], each[5]] for each in closestPointsList if each[0] == date]

    if len(list1) == 0:
        return
    
    lons1 = []
    lats1 = []
    lons2 = []
    lats2 = []
    for eachline in list1:
        lat1, lon1, lat2, lon2 = eachline
  
        lons1.append(lon1)
        lons2.append(lon2)
        lats1.append(lat1)
        lats2.append(lat2)   

    m.scatter(lons1, lats1, s=15, c=color_sat1, marker=('o'), linewidths=0, zorder=100)
    m.scatter(lons2, lats2, s=15, c=color_sat2, marker=('o'), linewidths=0, zorder=100)


def draw_fixed(sat2Nm, ymd_s, ymd_e, drew_points, out_fig_file):
    '''
    画固定点图
    '''
    fig = plt.figure(figsize=(8, 4.5))  # world
    ax = subplot(111)
    plt.subplots_adjust(left=0.09, right=0.95, bottom=0.11, top=0.97)

    drawFigs(fig, drew_points, True)

    circle1 = mpatches.Circle((60, 24), 6, color=RED, ec=EDGE_GRAY, lw=0.3)
    circle2 = mpatches.Circle((219, 24), 6, color=BLUE, ec=EDGE_GRAY, lw=0.3) 
    fig.patches.extend([circle1, circle2]) 
    
    fig.text(0.1, 0.04, 'Fixed Points', color=RED, fontproperties=FONT0)
    fig.text(0.3, 0.04, '%s' % sat2Nm, color=BLUE, fontproperties=FONT0)
    
    if ymd_s != ymd_e:
        fig.text(0.55, 0.04, '%s-%s' % (ymd_s, ymd_e), fontproperties=FONT0)
    else:
        fig.text(0.55, 0.04, '%s' % ymd_s, fontproperties=FONT0)
    fig.text(0.83, 0.04, ORG_NAME, fontproperties=FONT0)
    
    # 设定Map边框粗细
    spines = ax.spines
    for eachspine in spines:
        spines[eachspine].set_linewidth(0)
        
    out_fig_dir = os.path.dirname(out_fig_file)  # add 2015-10-16 10:30
    if not os.path.exists(out_fig_dir):
        os.makedirs(out_fig_dir)
    fig.savefig(out_fig_file, dpi=100)
    fig.clear()
    plt.close()
    
    
def draw_china(sat1Nm, sat2Nm, ymd_s, ymd_e, drew_points, out_fig_file):
    '''
    画 中国区图
    '''
    fig = plt.figure(figsize=(8, 6), dpi=100)  # china
    ax = subplot(111)
    plt.subplots_adjust(left=0.11, right=0.91, bottom=0.12, top=0.92)

    drawFigs(fig, drew_points, False)
    
    circle1 = mpatches.Circle((58, 36), 6, color=RED, ec=EDGE_GRAY, lw=0.3)
    circle2 = mpatches.Circle((219, 36), 6, color=BLUE, ec=EDGE_GRAY, lw=0.3) 
    fig.patches.extend([circle1, circle2]) 
    
    TEXT_Y = 0.05
    fig.text(0.1, TEXT_Y, '%s' % sat1Nm, color=RED, fontproperties=FONT0)
    fig.text(0.3, TEXT_Y, '%s' % sat2Nm, color=BLUE, fontproperties=FONT0)
    if ymd_s != ymd_e:
        fig.text(0.55, TEXT_Y, '%s-%s' % (ymd_s, ymd_e), fontproperties=FONT0)
    else:
        fig.text(0.55, TEXT_Y, '%s' % ymd_s, fontproperties=FONT0)
    fig.text(0.83, TEXT_Y, ORG_NAME, fontproperties=FONT0)
    
    # 设定Map边框粗细
    spines = ax.spines
    for eachspine in spines:
        spines[eachspine].set_linewidth(0)

    out_fig_dir = os.path.dirname(out_fig_file)  # add 2015-10-16 10:30
    if not os.path.exists(out_fig_dir):
        os.makedirs(out_fig_dir)
    fig.savefig(out_fig_file, dpi=100)
    fig.clear()
    plt.close()
    
def draw_world(sat1Nm, sat2Nm, ymd_s, ymd_e, drew_points, out_fig_file):
    '''
    画 全球图
    '''
    # 画图
    fig = plt.figure(figsize=(8, 4.5))  # world
    ax = subplot(111)
    plt.subplots_adjust(left=0.09, right=0.93, bottom=0.11, top=0.97)
    
    drawFigs(fig, drew_points, True)

    circle1 = mpatches.Circle((58, 33), 6, color=RED, ec=EDGE_GRAY, lw=0.3)
    circle2 = mpatches.Circle((219, 33), 6, color=BLUE, ec=EDGE_GRAY, lw=0.3) 
    fig.patches.extend([circle1, circle2]) 

    TEXT_Y = 0.06
    fig.text(0.1, TEXT_Y, '%s' % sat1Nm, color=RED, fontproperties=FONT0)
    fig.text(0.3, TEXT_Y, '%s' % sat2Nm, color=BLUE, fontproperties=FONT0)
    
    if ymd_s != ymd_e:
        fig.text(0.55, TEXT_Y, '%s-%s' % (ymd_s, ymd_e), fontproperties=FONT0)
    else:
        fig.text(0.55, TEXT_Y, '%s' % ymd_s, fontproperties=FONT0)
    fig.text(0.83, TEXT_Y, ORG_NAME, fontproperties=FONT0)
        
    # 设定Map边框粗细
    spines = ax.spines
    for eachspine in spines:
        spines[eachspine].set_linewidth(0)
       
    out_fig_dir = os.path.dirname(out_fig_file)  # add 2015-10-16 10:30
    if not os.path.exists(out_fig_dir):
        os.makedirs(out_fig_dir)
        
    fig.savefig(out_fig_file, dpi=100)
    fig.clear()
    plt.close()
            
def draw_polar(sat1Nm, sat2Nm, ymd_s, ymd_e, drew_points, out_fig_file):
    '''
    画 两极图
    '''
    fig = plt.figure(figsize=(8, 4.5))  # polar
    plt.subplots_adjust(left=0.09, right=0.93, bottom=0.11, top=0.94)
    drew_polar_Figs(fig, drew_points)
    
    circle1 = mpatches.Circle((58, 33), 6, color=RED, ec=EDGE_GRAY, lw=0.3)
    circle2 = mpatches.Circle((219, 33), 6, color=BLUE, ec=EDGE_GRAY, lw=0.3) 
    fig.patches.extend([circle1, circle2]) 
    
    TEXT_Y = 0.06
    fig.text(0.1, TEXT_Y, '%s' % sat1Nm, color=RED, fontproperties=FONT0)
    fig.text(0.3, TEXT_Y, '%s' % sat2Nm, color=BLUE, fontproperties=FONT0)
    if ymd_s != ymd_e:
        fig.text(0.55, TEXT_Y, '%s-%s' % (ymd_s, ymd_e), fontproperties=FONT0)
    else:
        fig.text(0.55, TEXT_Y, '%s' % ymd_s, fontproperties=FONT0)
    fig.text(0.83, TEXT_Y, ORG_NAME, fontproperties=FONT0)
    
    fig.subplots_adjust(wspace=0.1)
    
    out_fig_dir = os.path.dirname(out_fig_file)  # add 2015-10-16 10:30
    if not os.path.exists(out_fig_dir):
        os.makedirs(out_fig_dir)

    fig.savefig(out_fig_file, dpi=100)
    fig.clear()
    plt.close()

def drew_polar_Figs(fig, drew_points):
    '''
    setup north polar aimuthal equidistant basemap.
    The longitude lon_0 is at 6-o'clock, and the
    latitude circle boundinglat is tangent to the edge  
    of the map at lon_0.
    '''
    north_fig = fig.add_subplot(1, 2, 1)

    mn = Basemap(projection='npaeqd', boundinglat=59, lon_0=0, resolution='c')
    # mn.drawcoastlines(color='g')
    mn.drawmapboundary(linewidth=0.5) 
    mn.fillcontinents(color=GRAY)
    # draw parallels and meridians.
    mn.drawparallels(np.arange(60., 91., 10.), linewidth=LINE_WIDTH,
                     dashes=[100, .0001], color='white',
                     textcolor=EDGE_GRAY, fontproperties=TICKER_FONT)
    mn.drawmeridians(np.arange(-180., 180., 30.), linewidth=LINE_WIDTH, latmax=90, labels=[1, 0, 0, 1],
                     dashes=[100, .0001], color='white',
                     textcolor=EDGE_GRAY, fontproperties=TICKER_FONT)
    
    mn.drawparallels(np.arange(60., 91., 10.), linewidth=LINE_WIDTH / 2., labels=[0, 0, 0, 0],
                     dashes=[100, .0001], color='white')
    mn.drawmeridians(np.arange(-180., 180., 30.), linewidth=LINE_WIDTH / 2., latmax=90, labels=[0, 0, 0, 0],
                     dashes=[100, .0001], color='white')
    
    
    lat_labels = [(0.0, 90.0), (0.0, 80.0), (0.0, 70.0), (0.0, 60.0)]
    for lon, lat in (lat_labels):
        xpt, ypt = mn(lon, lat)
        north_fig.text(xpt - 500000, ypt - 100000, str(lat)[0:2] + u'°N', fontproperties=TICKER_FONT)

    north_fig.set_title("Northern Hemisphere", fontproperties=FONT0)
    
    # south polar region.
    south_fig = fig.add_subplot(1, 2, 2)
    ms = Basemap(projection='spaeqd', boundinglat=-59, lon_0=180, resolution='c')

    ms.drawmapboundary(linewidth=0.5) 
    ms.fillcontinents(color=GRAY)
    # draw parallels and meridians.
    ms.drawparallels(np.arange(-90., -50., 10.), linewidth=LINE_WIDTH,
                     dashes=[100, .0001], color='white',
                     textcolor=EDGE_GRAY, fontproperties=TICKER_FONT)  # ,labels=[0,1,0,0])
    ms.drawmeridians(np.arange(-180., 180., 30.), linewidth=LINE_WIDTH, latmax=90, labels=[0, 1, 0, 1],
                     dashes=[100, .0001], color='white',
                     textcolor=EDGE_GRAY, fontproperties=TICKER_FONT)

    ms.drawparallels(np.arange(-90., -50., 10.), linewidth=LINE_WIDTH / 2., labels=[0, 0, 0, 0],
                     dashes=[100, .0001], color='white')  # ,labels=[0,1,0,0])
    ms.drawmeridians(np.arange(-180., 180., 30.), linewidth=LINE_WIDTH / 2., latmax=90, labels=[0, 0, 0, 0],
                     dashes=[100, .0001], color='white')
    
    lat_labels = [(0.0, -90.0), (0.0, -80.0), (0.0, -70.0), (0.0, -60.0)]
    for lon, lat in (lat_labels):
        xpt, ypt = ms(lon, lat)
        south_fig.text(xpt + 500000, ypt + 200000, str(lat)[1:3] + u'°S', fontproperties=TICKER_FONT)
    
    south_fig.set_title("Southern Hemisphere", fontproperties=FONT0)
    
    for each in drew_points:
        sat1_lon, sat1_lat = each[0], each[1]
        sat2_lon, sat2_lat = each[2], each[3]
        
        sat1_lon_obts, sat1_lat_obts = each[4]
        sat2_lon_obts, sat2_lat_obts = each[5]
        
        if sat1_lat > 0 :
            north_fig = fig.add_subplot(1, 2, 1)
            if sat1_lon_obts is not None and sat1_lat_obts is not None:
                x_lons, y_lats = mn(sat1_lon_obts, sat1_lat_obts)
                mn.plot(x_lons, y_lats, '-', linewidth=1, color=RED)
            if sat2_lon_obts is not None and sat2_lat_obts is not None:
                x_lons, y_lats = mn(sat2_lon_obts, sat2_lat_obts)
                mn.plot(x_lons, y_lats, '-', linewidth=1, color=BLUE)

            x, y = mn(sat1_lon, sat1_lat)
            mn.plot(x, y, marker='o', linewidth=0, markerfacecolor=RED,
                    markeredgecolor=EDGE_GRAY, markersize=10.0, mew=0.2)
            x, y = mn(sat2_lon, sat2_lat)
            mn.plot(x, y, marker='o', linewidth=0, markerfacecolor=BLUE,
                    markeredgecolor=EDGE_GRAY, markersize=10.0, mew=0.2)
            # draw tissot's indicatrix to show distortion.

        else :
            south_fig = fig.add_subplot(1, 2, 2)
            if sat1_lon_obts is not None and sat1_lat_obts is not None:
                x_lons, y_lats = ms(sat1_lon_obts, sat1_lat_obts)
                ms.plot(x_lons, y_lats, '-', linewidth=1, color=RED)
            if sat2_lon_obts is not None and sat2_lat_obts is not None:
                x_lons, y_lats = ms(sat2_lon_obts, sat2_lat_obts)
                ms.plot(x_lons, y_lats, '-', linewidth=1, color=BLUE)

            x, y = ms(sat1_lon, sat1_lat)
            ms.plot(x, y, marker='o', linewidth=0, markerfacecolor=RED,
                    markeredgecolor=EDGE_GRAY, markersize=10.0, mew=0.2)
            x, y = ms(sat2_lon, sat2_lat)
            ms.plot(x, y, marker='o', linewidth=0, markerfacecolor=BLUE,
                    markeredgecolor=EDGE_GRAY, markersize=10.0, mew=0.2)

    # 设定Map边框粗细
    spines = north_fig.spines
    for eachspine in spines:
        spines[eachspine].set_linewidth(0)
    spines = south_fig.spines
    for eachspine in spines:
        spines[eachspine].set_linewidth(0)
                    
def drawFigs(fig, drew_points, world):
    '''
    create new figure
    '''
    if (world == False):
        m = Basemap(llcrnrlon=50., llcrnrlat=-40., urcrnrlon=150., urcrnrlat=40., \
            resolution='c', area_thresh=10000., projection='cyl', \
            lat_ts=20.)
    else :
        m = Basemap(llcrnrlon=-180., llcrnrlat=-90., urcrnrlon=180., urcrnrlat=90., \
            resolution='c', area_thresh=10000., projection='cyl', \
            lat_ts=20.)
        
    m.fillcontinents(color=GRAY)

    # draw parallels
    m.drawparallels(np.arange(90., -91., -30.), linewidth=LINE_WIDTH, labels=[1, 0, 0, 1],
                    dashes=[100, .0001], color='white',
                    textcolor=EDGE_GRAY, fontproperties=TICKER_FONT)
    # draw meridians
    m.drawmeridians(np.arange(-180., 180., 30.), linewidth=LINE_WIDTH, labels=[1, 0, 0, 1],
                    dashes=[100, .0001], color='white',
                    textcolor=EDGE_GRAY, fontproperties=TICKER_FONT)
    # draw parallels
    m.drawparallels(np.arange(60., -90., -30.), linewidth=LINE_WIDTH, labels=[0, 0, 0, 0],
                    dashes=[100, .0001], color='white')
    # draw meridians
    m.drawmeridians(np.arange(-150., 180., 30.), linewidth=LINE_WIDTH, labels=[0, 0, 0, 0],
                    dashes=[100, .0001], color='white')
    
    # plot
    for each in drew_points:
        sat1_lon, sat1_lat = each[0], each[1]
        sat2_lon, sat2_lat = each[2], each[3]
        
        sat1_lon_obts, sat1_lat_obts = each[4]
        sat2_lon_obts, sat2_lat_obts = each[5]
               
        if world == False:
            markersize = 8
        else :
            markersize = 6
        
        if sat1_lon_obts is not None and sat1_lat_obts is not None:
            x_lons, y_lats = m(sat1_lon_obts, sat1_lat_obts)
            draw_satTrail(x_lons, y_lats, RED, 0.8)
#             draw_satTrail_multicolor(x_lons, y_lats, 'Reds', 0.8)

        if sat2_lon_obts is not None and sat2_lat_obts is not None:
            x_lons, y_lats = m(sat2_lon_obts, sat2_lat_obts)
            draw_satTrail(x_lons, y_lats, BLUE, 0.8)
#             draw_satTrail_multicolor(x_lons, y_lats, 'Blues', 0.8)
        
        if sat1_lon is not None and sat1_lat is not None:
            x, y = m(sat1_lon, sat1_lat)
            m.plot(x, y, marker='o', linewidth=0, markerfacecolor=RED, markeredgecolor=EDGE_GRAY, markersize=markersize, mew=0.2)
        if sat2_lon is not None and sat2_lat is not None:
            x, y = m(sat2_lon, sat2_lat)
            m.plot(x, y, marker='o', linewidth=0, markerfacecolor=BLUE, markeredgecolor=EDGE_GRAY, markersize=markersize, mew=0.2)
    
                                
if __name__ == '__main__':
    pass
