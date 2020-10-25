'''
Created on Sep 19, 2020

@author: esdev
'''

import socket
import collections
from contextlib import closing
import netifaces
from slacm.config import Config

NetInfo = collections.namedtuple('NetInfo','globalHost localHost macAddress')

def get_network_interfaces(nicName=None):
    '''
     Determine the IP address of  the network interfaces
     Return a tuple of list of global IP addresses, list of MAC addresses, and local IP address
     ''' 
    if nicName is None:
        nicName = Config.NIC_NAME
    local = None
    ipAddressList = []
    macAddressList = []
    ifNameList = []
    ifNames = netifaces.interfaces()
    found = False    
    for ifName in ifNames:
        ifInfo = netifaces.ifaddresses(ifName)
        if netifaces.AF_INET in ifInfo:
            ifAddrs = ifInfo[netifaces.AF_INET]
            ifAddr = ifAddrs[0]['addr']
            if ifAddr == '127.0.0.1':
                local = ifAddr
            else:
                ipAddressList.append(ifAddr)
                ifNameList.append(ifName)
                linkAddrs = netifaces.ifaddresses(ifName)[netifaces.AF_LINK]
                linkAddr = linkAddrs[0]['addr'].replace(':','')
                macAddressList.append(linkAddr)
                if(nicName == ifName):
                    ipAddressList = [ipAddressList[-1]]
                    macAddressList = [macAddressList[-1]] 
                    found = True
                    break
    return (ipAddressList,macAddressList,ifNameList,local,found)

def find_free_port():
    '''
    Find a free (available) port number.
    '''
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]
    
if __name__ == '__main__':
    pass