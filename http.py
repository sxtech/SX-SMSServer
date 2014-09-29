# -*- coding: cp936 -*-
import httplib2

#获取HTTP对象
class HttpFetch:
    def __init__(self,host,port,timeout=10,trys=1):
        self.h    = httplib2.Http()
        self.host = host
        self.port = port
        self.trys = trys
        self.timeout = timeout
        
    def __del__(self):
        del self.h

    def sendMsg(self,tel,conts):
        cont = ''
        if conts != None:
            cont = conts.replace(' ','%20')
        resp, content = self.h.request("http://%s:%s/sms/index.php/sendmsg/send_msg?tel=%s&content=%s"%(self.host,self.port,tel,cont))
        return content

    def connTest(self):
        resp, content = self.h.request("http://%s:%s/sms/index.php/sendmsg/conn_test"%(self.host,self.port))
        return content

if __name__ == "__main__":
    hf = HttpFetch('localhost',8082)
    a = hf.sendMsg(15819851862,'show me the money')
    #print (hf.connTest()[:2],)
    import json
    print json.loads(a)['result']
