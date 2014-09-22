# -*- coding: cp936 -*-
import MySQLdb
import gl

class Smysql:
    def __init__(self):
        self.conn = gl.mysqlpool.connection()
        self.cur  = self.conn.cursor(cursorclass = MySQLdb.cursors.DictCursor)
        
    def __del__(self):
        try:
            self.cur.close()
            self.conn.close()
        except Exception,e:
            pass

    def addSMS(self,values):
        try:
            self.cur.executemany("insert into smsser (host,time,tel,content,result) values(%s,%s,%s,%s,%s)",values)
        except MySQLdb.Error,e:
            self.conn.rollback()
            raise
        else:
            self.conn.commit()

    def getSMS(self,valid=0):
        try:
            self.cur.execute("select * from smsser where valid=%s"%valid)
            s = self.cur.fetchall()
            self.conn.commit()
        except MySQLdb.Error,e:
            self.conn.rollback()
            raise
        else:
            return s

    #获取最大ID
    def getMaxID(self):
        try:
            self.cur.execute("select max(id) as id from smsser")
            s = self.cur.fetchone()
            self.conn.commit()
        except MySQLdb.Error,e:
            self.conn.rollback()
            raise
        else:
            return s

    #根据ID号获取短信信息
    def getSMSByID(self,idlist,valid=0):
        #print 'idlist',idlist
        #print "select * from smsser where id in(%s) and valid=%s"%(','.join(idlist),valid)
        try:
            self.cur.execute("select * from smsser where id in(%s) and valid=%s"%(','.join(idlist),valid))
            s = self.cur.fetchall()
            self.conn.commit()
        except MySQLdb.Error,e:
            self.conn.rollback()
            raise
        else:
            return s

    def updateSMS(self,_id,result,valid):
        try:
            self.cur.execute("update smsser set result='%s', valid=%s where id=%s"%(str(result),valid,_id))
            self.conn.commit()
        except MySQLdb.Error,e:
            self.conn.rollback()
            raise
        
    def endOfCur(self):
        self.conn.commit()
        
    def sqlCommit(self):
        self.conn.commit()
        
    def sqlRollback(self):
        self.conn.rollback()
            
if __name__ == "__main__":
    from DBUtils.PooledDB import PooledDB
    import datetime
    import threading
    
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

    mysqlPool('localhost','root','',3306)
    
    mysql = Smysql()
    #values=[('127.0.0.1',datetime.datetime.now(),123,'测试','结果')]
    s = mysql.getSMSByID(['1'])
    print s[0]['content'].encode('gbk')
    del mysql
    

    

