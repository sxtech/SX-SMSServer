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

logger = logging.getLogger('root')  #������־�ļ�����

def mysqlPool(h,u,ps,pt,minc=5,maxc=20,maxs=10,maxcon=100,maxu=1000):
    gl.mysqlpool = PooledDB(
        MySQLdb,
        host = h,
        user = u,
        passwd = ps,
        db = "sms",
        charset = "gbk",
        mincached = minc,        #����ʱ�����Ŀ���������
        maxcached = maxc,        #���ӳ���������������
        maxshared = maxs,        #���ӳ����ɹ�����������
        maxconnections = maxcon, #���������������
        maxusage = maxu)
    
class SMSSer:
    def __init__(self):
        self.smsIni = SMSIni()
        #��������
        self.sysset = self.smsIni.getSysConf()
        self.port   = self.sysset['port']
        #sms����
        self.smsset  = self.smsIni.getSMSConf()
        self.iplist  = self.smsset['ip'].split(',')
        self.smsport = self.smsset['port']

        #mysql����
        self.mysqlini = self.smsIni.getMysqlConf()
        self.mysqlHost = self.mysqlini['host']
        self.mysqlflag  = False   #mysql ��¼���
        self.mysqlCount = 0       #mysql ��¼����

        self.pq = Queue.PriorityQueue()      #�������ȼ�����
        self.sq = Queue.Queue()              #�������
        self.fq = Queue.Queue()              #ʧ�ܷ������

        self.hf = HelpFunc()


    #��¼mysql
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

    #���Ӳ���
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

    #���ŷ��Ͳ���
    def sendCheck(self):
        h = HttpFetch('127.0.0.1',self.smsport)
        fail_list = []    #ʧ�ܷ���IP����
        count = 0
        while 1:
            #�˳����
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
                            self.sq.put({'ip':i,'fails':0})  #���IP������
                    except Exception,e:
                        gl.TRIGGER.emit("<font %s>%s</font>"%(gl.style_red,self.hf.getTime()+i+str(e)))
                        logger.error(i+str(e))
                count = 0
            else:                
                count += 1
            
            time.sleep(1)
            
    #��ѭ��
    def main(self): 
        logger.info('Logon System')
        #�ѷ���IP�������
        self.connCheck()

        t3 = threading.Thread(target=self.sendCheck)
        t3.start()
        while 1:
            #�˳����
            if not gl.QTFLAG:
                gl.DCFLAG = False
                del self.smsIni
                logger.warning('Logout System')
                break

            #��¼���
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

    #��Ӷ��ŵ�����
    def putSMS(self):
        mysql = Smysql()
        try:
            self.pq = Queue.PriorityQueue()   #�������
            maxid = 0  #���ID

            while 1:
                #�˳����
                #print 'maxid',maxid
                if not gl.QTFLAG:
                    gl.DCFLAG = False
                    break

                if not self.mysqlflag:
                    break
                newid = mysql.getMaxID()['id']  #��ȡ���ID

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

    #���Ͷ���  
    def sendSMS(self):
        while 1:
            try:
                #�˳����
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
                    gl.TRIGGER.emit("<font %s>%s</font>"%(gl.style_blue,self.hf.getTime()+'�绰:'+str(sms[1]['tel'])+'_����:'+str(content)))
                else:
                    time.sleep(1)
            except Exception,e:
                logger.error(e)
                gl.TRIGGER.emit("<font %s>%s</font>"%(gl.style_red,self.hf.getTime()+str(e)))        
                time.sleep(1)

    #���Ͷ���HTTP����
    def httpRequest(self,ip_dict,sms):
        ms = Smysql()
        http_ip = ip_dict['ip']    #����IP
        fails = ip_dict['fails']   #ʧ�ܴ���
        h = HttpFetch(http_ip,self.smsport)
        valid  = -1
        result = ''
        
        #���Ͷ���
        try:
            result = h.sendMsg(sms['tel'],sms['content']) #����content��UTF8
            if result[:2] == '-1' or '-2':
                valid = -1
                fails = ip_dict['fails']+1      #ʧ�ܴ�����1
            else:
                valid = 1
                fails = 0          #ʧ�ܴ�����0
        except Exception,e:
            result = '-2'
            fails = ip_dict['fails']+1      #ʧ�ܴ�����1
            logger.error(http_ip+str(e))
            gl.TRIGGER.emit("<font %s>%s</font>"%(gl.style_red,self.hf.getTime()+http_ip+str(e)))        
        #���¶�������
        try:
            ms.updateSMS(sms['id'],result,valid)
        except MySQLdb.Error,e:
            self.mysqlflag = False
            self.mysqlCount = 1
            gl.TRIGGER.emit("<font %s>%s</font>"%(gl.style_red,self.hf.getTime()+str(e)))
            logger.error(e)
            
        if fails >= 3:              #����ʧ�ܴ���3�������ʧ�ܷ������
            self.fq.put(http_ip)
        else:
            self.sq.put({'ip':http_ip,'fails':fails}) #����IP������
        
        del ms
        del h



if __name__ == '__main__':
    s = SMSSer()
    s.main()
