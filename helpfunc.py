# -*- coding: cp936 -*-
import datetime

class HelpFunc:
    def getTime(self):
        return datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

    def ipToBigint(self,ipaddr):
        ipStrs = ipaddr.split(".")

        return str(int(ipStrs[3]) + int(ipStrs[2])*256 + int(ipStrs[1])*256*256 + int(ipStrs[0])*256*256*256) 


    def bigintToIp(self,intStr):
        bigint = int(intStr)

        first = bigint/(256*256*256)
        rest = bigint - (first*256*256*256)
        
        second = rest/(256*256)
        rest -= second*256*256
        
        third = rest/256    
        fourth = rest - third * 256
        
        return "%d.%d.%d.%d"%(first,second,third,fourth)

if __name__ == '__main__':
    hf = HelpFunc()
    print hf.getTime()
