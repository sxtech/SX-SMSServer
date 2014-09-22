#-*- encoding: gb2312 -*-
import ConfigParser

class SMSIni:
    def __init__(self,confpath = 'sms.conf'):
        self.path = ''
        self.confpath = confpath
        self.cf = ConfigParser.ConfigParser()
        self.cf.read(confpath)

    def getSysConf(self):
        syst = {}
        syst['port']    = self.cf.get('SYSSET','port')
        return syst

    def setSysConf(self,port):
        self.cf.set('SYSSET','port',port)
        fh = open(self.confpath, 'w')
        self.cf.write(fh)
        fh.close()

    def getSMSConf(self):
        smsset = {}
        smsset['ip']   = self.cf.get('SMSSET','ip')
        smsset['port'] = self.cf.getint('SMSSET','port')
        return smsset

    def getMysqlConf(self):
        mysqlconf = {}
        mysqlconf['host']    = self.cf.get('MYSQLSET','host')
        mysqlconf['user']    = self.cf.get('MYSQLSET','user')
        mysqlconf['passwd']  = self.cf.get('MYSQLSET','passwd')
        mysqlconf['port']    = self.cf.getint('MYSQLSET','port')
        mysqlconf['mincached']      = self.cf.getint('MYSQLSET','mincached')
        mysqlconf['maxcached']      = self.cf.getint('MYSQLSET','maxcached')
        mysqlconf['maxshared']      = self.cf.getint('MYSQLSET','maxshared')
        mysqlconf['maxconnections'] = self.cf.getint('MYSQLSET','maxconnections')
        mysqlconf['maxusage']       = self.cf.getint('MYSQLSET','maxusage')
        return mysqlconf
     
if __name__ == "__main__":

    try:
        ftpini = DataCenterIni()
        print ftpini.getSysConf()

    except ConfigParser.NoOptionError,e:
        print e
        time.sleep(10)


