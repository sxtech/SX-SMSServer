# -*- coding: cp936 -*-
import socket
import Queue
import threading
import time
import logging
import MySQLdb
import gl
from helpfunc import HelpFunc
from mysqldb import Smysql
from iniconf import SMSIni
from http import HttpFetch
from DBUtils.PooledDB import PooledDB

TIMEOUT = 40

logger = logging.getLogger('root')  #创建日志文件对象

def mysqlPool(h,u,ps,pt,minc=5,maxc=20,maxs=10,maxcon=100,maxu=1000):
    gl.mysqlpool = PooledDB(
        MySQLdb,
        host = h,
        user = u,
        passwd = ps,
        db = "sms",
        charset = "gbk",
        mincached = minc,        #启动时开启的空连接数量
        maxcached = maxc,        #连接池最大可用连接数量
        maxshared = maxs,        #连接池最大可共享连接数量
        maxconnections = maxcon, #最大允许连接数量
        maxusage = maxu)
    
class SMSSer:
    def __init__(self):
        self.smsIni = SMSIni()
        #本地设置
        self.sysset = self.smsIni.getSysConf()
        self.port   = self.sysset['port']
        #sms设置
        self.smsset  = self.smsIni.getSMSConf()
        self.iplist  = self.smsset['ip'].split(',')
        self.smsport = self.smsset['port']

        #mysql设置
        self.mysqlini = self.smsIni.getMysqlConf()
        self.mysqlHost = self.mysqlini['host']
        self.mysqlflag  = False   #mysql 登录标记
        self.mysqlCount = 0       #mysql 登录计数

        self.pq = Queue.PriorityQueue()      #短信优先级队列
        self.sq = Queue.Queue()              #服务队列

        self.hf = HelpFunc()


    #登录mysql
    def loginMysql(self):
        try:
            gl.TRIGGER.emit("<font %s>%s</font>"%(gl.style_green,self.hf.getTime()+'Start to login mysql...'))
            mysqlPool(self.mysqlini['host'],self.mysqlini['user'],self.mysqlini['passwd'],3306,self.mysqlini['mincached'],self.mysqlini['maxcached'],
                      self.mysqlini['maxshared'],self.mysqlini['maxconnections'],self.mysqlini['maxusage'])
            self.mysqlflag = True
            gl.TRIGGER.emit("<font %s>%s</font>"%(gl.style_green,self.hf.getTime()+'Login mysql success!'))
            self.mysqlCount = 0
        except Exception,e:
            self.mysqlflag = False
            gl.TRIGGER.emit("<font %s>%s</font>"%(gl.style_red,self.hf.getTime()+str(e)))
            self.mysqlCount = 1
            
    #主循环
    def main(self): 
        logger.info('Logon System')
        #把服务IP加入队列
        for i in self.iplist:
            self.sq.put(i)
            
        while 1:
            #退出检测
            if not gl.QTFLAG:
                gl.DCFLAG = False
                del self.smsIni
                logger.warning('Logout System')
                break

            #登录检测
            if self.mysqlflag:
                t1 = threading.Thread(target=self.putSMS)
                t2 = threading.Thread(target=self.sendSMS)
                t1.start()
                t2.start()
                t1.join()
                t2.join()
            else:
                if self.mysqlCount==0 or self.mysqlCount>15:
                    self.loginMysql()
                else:
                    self.mysqlCount += 1

            time.sleep(1)

    #添加短信到队列
    def putSMS(self):
        mysql = Smysql()
        try:
            self.pq = Queue.PriorityQueue()   #清除队列
            maxid = 0  #最大ID

            while 1:
                #退出检测
                #print 'maxid',maxid
                if not gl.QTFLAG:
                    gl.DCFLAG = False
                    break

                if not self.mysqlflag:
                    break
                newid = mysql.getMaxID()['id']  #获取最大ID

                if newid != None and newid > maxid:
                    idlist = []
                    for i in range(maxid,newid):
                        idlist.append(str(i+1))
                    newunvalid = mysql.getSMSByID(idlist)

                    for i in newunvalid:
                        self.pq.put((i['level'],{'id':i['id'],'tel':i['tel'],'content':i['content']}))
                    maxid = newid
                time.sleep(1)
        except MySQLdb.Error,e:
            self.mysqlflag = False
            self.mysqlCount = 1
            gl.TRIGGER.emit("<font %s>%s</font>"%(gl.style_red,self.hf.getTime()+str(e)))
            logger.error(e)
            
        del mysql

    #发送短信  
    def sendSMS(self):
        while 1:
            try:
                #退出检测
                if not gl.QTFLAG:
                    gl.DCFLAG = False
                    break
                
                if not self.mysqlflag:
                    break
                elif self.pq.empty()==False and self.sq.empty()==False:
                    sms = self.pq.get()
                    ip  = self.sq.get()
                    t = threading.Thread(target=self.httpRequest, args=(ip,sms[1]))
                    t.start()
                    if sms[1]['content'] == None:
                        content = 'None'
                    else:
                        content = sms[1]['content'].encode('gbk')
                    gl.TRIGGER.emit("<font %s>%s</font>"%(gl.style_blue,self.hf.getTime()+'电话:'+str(sms[1]['tel'])+'_内容:'+str(content)))
                else:
                    time.sleep(1)
            except Exception,e:
                logger.error(e)
                gl.TRIGGER.emit("<font %s>%s</font>"%(gl.style_red,self.hf.getTime()+str(e)))        
                time.sleep(1)

    #发送短信HTTP请求
    def httpRequest(self,http_ip,sms):
        ms = Smysql()
        h = HttpFetch(http_ip,self.smsport)
        valid  = -1
        result = ''
        
        #发送短信
        try:
            result = h.sendMsg(sms['tel'],sms['content']) #这里content是UTF8
            if result[:2] == '-1':
                valid = -1
            else:
                valid = 1
        except Exception,e:
            logger.error(e)
            gl.TRIGGER.emit("<font %s>%s</font>"%(gl.style_red,self.hf.getTime()+str(e)))        
        #更新短信内容
        try:
            ms.updateSMS(sms['id'],result,valid)
        except MySQLdb.Error,e:
            self.mysqlflag = False
            self.mysqlCount = 1
            gl.TRIGGER.emit("<font %s>%s</font>"%(gl.style_red,self.hf.getTime()+str(e)))
            logger.error(e)
            
        self.sq.put(http_ip) #回收IP到队列
        
        del ms
        del h



if __name__ == '__main__':
    s = SMSSer()
    s.main()
