# coding: utf-8

__Author__ = "ys"
__Date__ = '2018/05/10 '

import os, sys, re, pdb
import yaml
import urllib, requests
from datetime import datetime
import urllib3
urllib3.disable_warnings()

# 配置文件信息，设置为全局
MainPath, MainFile = os.path.split(os.path.realpath(__file__))
YamlFile = os.path.join(MainPath, 'dm_odm_order_core.yaml')


def set_newValue (dataDict, key, value):
	'''
	repalce  dict of list ,use key
	'''
	for vdict in dataDict:
		if key in vdict.keys():
			vdict[key] = value

class ReadYaml():

	def __init__(self, sat, sensor):
		"""
		读取yaml格式配置文件
		"""
		if not os.path.isfile(YamlFile):
			print 'Not Found %s' % YamlFile
			sys.exit(-1)

		with open(YamlFile, 'r') as stream:
			cfg = yaml.load(stream)

		dtype = sat + '+' + sensor
		self.user = cfg['web01']['user']
		self.pawd = cfg['web01']['pawd']
		self.mail = cfg['web01']['mail']
		self.urlType = cfg[dtype]['url_type']
		self.body_data = cfg[dtype]['body_data']
		self.mail_data = cfg[dtype]['mail_data']

class WEBORDER(object):
	"""
	构造请求数据
	"""
	def __init__(self, inCfg):

		self.url_open = 'https://www.class.ngdc.noaa.gov/saa/products/classlogin?resource=%2Fsaa%2Fproducts%2Fwelcome'
		self.url_login = 'https://www.class.ngdc.noaa.gov/saa/products/j_security_check'
		self.s = requests.Session()
		self.s.verify = False  # 取消安全认证

		# 加headers 伪造请求头。
		self.inCfg = inCfg
		self.timeout = 60  # 请求超时时间设置
		self.s.headerss = {
			'User-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.117 Safari/537.36',
			 'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
			 'Accept-Encoding':'gzip, deflate, br',
			 # 'Content-Length': '43',
			 'Cache-Control': 'no-cache',
			 'Host':'www.class.ngdc.noaa.gov',
			 'Origin':'https://www.class.ngdc.noaa.gov',
			 'Upgrade-Insecure-Requests':'1',
			 'Accept-Language': 'zh-CN,zh;q=0.9',
			 'Connection':'keep-alive',
			 'Pragma': 'no-cache',
			 # 'Save-Data': 'on',
			 # 'DNT': '1',
			 # "x-insight": "activate",
			 'Content-Type':'application/x-www-form-urlencoded',
			 'Referer':'https://www.class.ngdc.noaa.gov/saa/products/classlogin?resource=/saa/products/welcome'}


	def get_cookie_token(self):
		"""
		因为登录时需要先获取csrfToken值，所以先get获取，
		然后在下方post数据的时候使用。
		:return: csrfToken
		"""
		page = self.s.get(self.url_open, timeout=self.timeout)
		# pdb.set_trace()
		for c in page.cookies:
			pass
# 			print c.name, c.value

		# JSESSIONID = page.cookies['value']
		return c.value

	def write_to_log(self, log_file, text):
		'''
		写入日志文件
		'''
		now = datetime.now()
		str_now = now.strftime("%Y-%m-%d %H:%M:%S")
		# print text
		log = open(log_file, 'a')
		log.write(str_now + "\t" + text + "\n")
		log.close()

	def login_fn(self):
		'''
		开始登陆
		'''
		csrfToken = self.get_cookie_token()
# 		print 'cookie=', csrfToken
		for key in self.s.headerss:
			self.s.headers[key] = self.s.headerss[key]
		# self.s.headers['Cookie']='JSESSIONID='+csrfToken
		data = urllib.urlencode({"j_username":self.inCfg.user, "j_password":self.inCfg.pawd})
		req = self.s.post(url=self.url_login, headers=self.s.headers, data=data, timeout=self.timeout)
		newCOOKIE = req.headers["set-Cookie"].split(";")[0]
		self.s.headers['Cookie'] = newCOOKIE  # 获得登陆成功的cookie

	def get_ordernum(self, sat, sensor, stime, etime):

		url_order = 'https://www.class.ngdc.noaa.gov/saa/prod/orderNow'
		url_type = self.inCfg.urlType
		url_order_num = 'https://www.class.ngdc.noaa.gov/saa/products/shopping_cart'
		url_datatime = 'https://www.class.ngdc.noaa.gov/saa/products/welcome'
		url_email = 'https://www.class.ngdc.noaa.gov/saa/products/shop'

		self.s.headers['Referer'] = url_datatime
		req_datatime = self.s.get(url_type, timeout=self.timeout)
		'''
		获取对应资料的数据起始、结束时间
		'''
		data_start = (re.compile('<input type="hidden" name="data_start" ([\s\S]*?)<input type="hidden"').findall(req_datatime.text)[0]).split("=")[-1][:-1]
		data_end = (re.compile('<input type="hidden" name="data_end" ([\s\S]*?)<input type="hidden"').findall(req_datatime.text)[0]).split("=")[-1][:-1]
		max_days_val = (re.compile('<input type="hidden" name="max_days_val" ([\s\S]*?)>').findall(req_datatime.text)[0]).split("=")[-1]
		self.s.headers['Referer'] = url_type

		start_date, start_time = stime.split()
		end_date, end_time = etime.split()
		# print 'data_start' , data_start.replace('"', '')
		# print 'data_end' , data_end
		# print 'max_days_val' , max_days_val.replace('"', '')
		data = []

		# 替换页面返回的信息，用于bodydata封装
		# print self.inCfg.body_data
		set_newValue(self.inCfg.body_data, 'data_start', data_start)
		set_newValue(self.inCfg.body_data, 'data_end', data_end)
		set_newValue(self.inCfg.body_data, 'max_days_val', max_days_val)
		set_newValue(self.inCfg.body_data, 'start_date', start_date)
		set_newValue(self.inCfg.body_data, 'start_time', start_time)
		set_newValue(self.inCfg.body_data, 'end_date', end_date)
		set_newValue(self.inCfg.body_data, 'end_time', end_time)
# 		print self.inCfg.body_data
		# 字典转list
		for v in self.inCfg.body_data:
			for v1, v2 in v.items():
				data.append((v1, v2))

		data = urllib.urlencode(data)
		# pdb.set_trace()
		response = self.s.post(url=url_order, headers=self.s.headers, data=data, timeout=self.timeout)
		response_order_number = self.s.get(url_order_num, timeout=self.timeout)
		# self.write_to_log('log.html', response.content)

		Size = re.compile('<size>([\s\S]*?)</size>').findall(response.text)[0]  # 获取返回的字节数总大小
# 		Ordernumber = re.compile('<hits>([\s\S]*?)</hits>').findall(response.text)[0]
# 		print 'size', Size
		# 替换页面返回的信息，用于maildata封装
		email_data = []
		set_newValue(self.inCfg.mail_data, 'order_size', Size)
		set_newValue(self.inCfg.mail_data, 'email', self.inCfg.mail)

		# 字典转list
		for v in self.inCfg.mail_data:
			for v1, v2 in v.items():
				email_data.append((v1, v2))
		# print email_data

		# pdb.set_trace()
		self.s.headers['Referer'] = url_order_num
		email_data = urllib.urlencode(email_data)
		testt = self.s.post(url=url_email, headers=self.s.headers, data=email_data, timeout=self.timeout)  # 发送邮件
		# self.write_to_log('log1.html', testt.content)
		orderID = (re.compile('Your confirmation number is:\n([\s\S]*?)<br>').findall(testt.text)[0]).strip()[:-1]
		return orderID

if __name__ == '__main__':
	ycfg = ReadYaml('NPP', 'CRIS')
	weborder = WEBORDER(ycfg)
	weborder.login_fn()
	Number = weborder.get_ordernum('NPP', 'CRIS', '2018-05-10 04:00:00', '2018-05-10 04:10:00')

	print  'ordernum=', Number
	print  'NPP CRIS'

