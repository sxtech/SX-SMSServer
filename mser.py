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
        self.fq = Queue.Queue()              #失败服务队列

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

    #连接测试
    def connCheck(self):
        httpf = HttpFetch('127.0.0.1',self.smsport)
        for i in self.iplist:
            try:
                httpf.host = i
                if httpf.connTest()[:2] != '-1':
                    self.sq.put({'ip':i,'fails':0})
            except Exception,e:
                gl.TRIGGER.emit("<font %s>%s</font>"%(gl.style_red,self.hf.getTime()+i+str(e)))
                logger.error(i+str(e))
        del httpf

    #短信发送测试
    def sendCheck(self):
        h = HttpFetch('127.0.0.1',self.smsport)
        fail_list = []    #失败服务IP链表
        count = 0
        while 1:
            #退出检测
            if not gl.QTFLAG:
                gl.DCFLAG = False
                del self.smsIni
                logger.warning('Logout System')
                break
            
            if self.fq.empty()==False:
                fail_list.append(self.fq.get())
                count = 31
                
            if count > 30:
                for i in fail_list:
                    try:
                        h.host = i
                        res = h.sendMsg(15819851862,'Hello World')
                        if result[:2] == '-1' or '-2':
                            pass
                        else:
                            fail_list.remove(i)
                            self.sq.put({'ip':i,'fails':0})  #添加IP到队列
                    except Exception,e:
                        gl.TRIGGER.emit("<font %s>%s</font>"%(gl.style_red,self.hf.getTime()+i+str(e)))
                        logger.error(i+str(e))
                count = 0
            else:                
                count += 1
            
            time.sleep(1)
            
    #主循环
    def main(self): 
        logger.info('Logon System')
        #把服务IP加入队列
        self.connCheck()

        t3 = threading.Thread(target=self.sendCheck)
        t3.start()
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
                    t = threading.Thread(target=self.httpRequest, args=(self.sq.get(),sms[1]))
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
    def httpRequest(self,ip_dict,sms):
        ms = Smysql()
        http_ip = ip_dict['ip']    #服务IP
        fails = ip_dict['fails']   #失败次数
        h = HttpFetch(http_ip,self.smsport)
        valid  = -1
        result = ''
        
        #发送短信
        try:
            result = h.sendMsg(sms['tel'],sms['content']) #这里content是UTF8
            if result[:2] == '-1' or '-2':
                valid = -1
                fails = ip_dict['fails']+1      #失败次数加1
            else:
                valid = 1
                fails = 0          #失败次数清0
        except Exception,e:
            result = '-2'
            fails = ip_dict['fails']+1      #失败次数加1
            logger.error(http_ip+str(e))
            gl.TRIGGER.emit("<font %s>%s</font>"%(gl.style_red,self.hf.getTime()+http_ip+str(e)))        
        #更新短信内容
        try:
            ms.updateSMS(sms['id'],result,valid)
        except MySQLdb.Error,e:
            self.mysqlflag = False
            self.mysqlCount = 1
            gl.TRIGGER.emit("<font %s>%s</font>"%(gl.style_red,self.hf.getTime()+str(e)))
            logger.error(e)
            
        if fails >= 3:              #发送失败大于3次则加入失败服务队列
            self.fq.put(http_ip)
        else:
            self.sq.put({'ip':http_ip,'fails':fails}) #回收IP到队列
        
        del ms
        del h



if __name__ == '__main__':
    s = SMSSer()
    s.main()
