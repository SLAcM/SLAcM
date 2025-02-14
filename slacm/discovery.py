'''
Created on Sep 26, 2020

@author: esdev
'''

import logging
import threading
import asyncio
import zmq
import zmq.asyncio
import time
import traceback
import sys
from slacm.utils import find_free_port
from slacm.config import Config

from kademlia.network import Server

SLAM_DS='tcp://127.0.0.1:'

class RootServer(threading.Thread):
    '''
    Root discovery server thread - runs in the 'root' app. 
    '''
    def __init__(self,port,interface):
        threading.Thread.__init__(self)
        self.logger = logging.getLogger(__name__)
        self.logger.info('RootServer(%d,%s)',port,interface)
        self.port = port
        self.interface = interface
       
    def run(self):
        self.loop = asyncio.new_event_loop()
        self.loop.set_debug(True)
        self.server = Server()
        self.logger.info('RootServer.run.listen()')
        self.loop.run_until_complete(self.server.listen(self.port,self.interface))
        self.logger.info('RootServer.run_forever()')
        try:
            self.loop.run_forever()
        except:
            traceback.print_exc()
        self.logger.info("root terminated")
    
    def stop(self):
        for cb in [self.server.stop, self.loop.stop]:
            self.loop.call_soon_threadsafe(cb)

class PeerServer(threading.Thread):
    '''
    Peer discovery server thread - each host (root and peer alike)
    runs a copy of this. Peer nodes connect via the root node's RootServer.
    '''
    SLAM_DS_GET='g'
    SLAM_DS_SET='s'
    SLAM_DS_HALT='h'
    def __init__(self,rootHostPort,peerPort,localPort):
        threading.Thread.__init__(self)
        self.logger = logging.getLogger(__name__)
        self.logger.info('PeerServer(root=%r,peer=%r,local=%r)',rootHostPort,peerPort,localPort)
        self.daemon = True
        self.rootServer = rootHostPort
        self.peerPort = peerPort
        self.localPort = localPort
        self.server = None
        self.ctx = zmq.asyncio.Context.instance()
        
    async def peer(self):
        self.ctrl = self.ctx.socket(zmq.REP)
        self.ctrl.bind(SLAM_DS+str(self.localPort))
        self.server = Server()
        self.logger.info('PeerServer.peer.listen()')
        await self.server.listen(self.peerPort)
        self.logger.info('PeerServer.peer.bootstrap()')
        await self.server.bootstrap([self.rootServer])
        stop = False
        self.logger.info('PeerServer.run()')
        while not stop:
            msg = await self.ctrl.recv_pyobj()
            if msg[0] == PeerServer.SLAM_DS_GET:
                rsp = await self.server.get(msg[1])
            elif msg[0] == PeerServer.SLAM_DS_SET:
                rsp = await self.server.set(msg[1],msg[2])
            elif msg[0] == PeerServer.SLAM_DS_HALT:
                rsp = 'done'
                stop = True
            else:
                rsp = '???'
            await self.ctrl.send_pyobj(rsp)
        self.server.stop()

    def run(self):
        asyncio.run(self.peer())
        self.logger.info("peer terminated")

class DiscoveryService(object):
    '''
    Discovery service class  - instantiated by the App (on the root and peer nodes alike). 
    Acts as the interface of the App to the discovery service. 
    '''
    def __init__(self,context,interface,root_port=None):
        self.logger = logging.getLogger(__name__)
        self.interface = interface
        self.root_port = root_port
        self.ctx = context
        
        if self.root_port is None:
            self.root_port = find_free_port()
            self.root_server = RootServer(port=self.root_port,interface=self.interface)
            self.root_server.start()
            time.sleep(1)
        else:
            self.root_server = None
        
        self.peer_port = find_free_port()
        self.local_port = find_free_port()
        self.peer_server = PeerServer((self.interface,self.root_port),self.peer_port,self.local_port)
        
        self.peer_server.start()
        self.command = self.ctx.socket(zmq.REQ)
        self.command.connect(SLAM_DS+str(self.local_port))

    def get_local_port(self):
        return self.local_port
    
    def root(self):
        if self.root_server:
            return self.interface,self.root_port
        else:
            return None
    
    def call(self,msg):
        self.logger.info('send: %s' % str(msg))
        self.command.send_pyobj(msg)
        rsp = self.command.recv_pyobj()
        self.logger.info('recv: %s' % str(rsp))
        return rsp

    def get(self,key):
        return self.call((PeerServer.SLAM_DS_GET,key))
    
    def set(self,key,value):
        return self.call((PeerServer.SLAM_DS_SET,key,value))
    
    def stop(self):
        res = self.call((PeerServer.SLAM_DS_HALT,))
        self.peer_server.join()
        if self.root_server:
            self.root_server.stop()
            self.root_server.join()
        return res
    
class DiscoveryClient(object):
    '''
    Discovery service client - each component has a copy of this.  
    Acts as the interface of the Component to the discovery service. 
    '''
    def __init__(self,context,service):
        self.logger = logging.getLogger(__name__)
        self.ctx = context
        self.local_port = service.get_local_port()
        
        self.command = self.ctx.socket(zmq.REQ)
        self.command.connect(SLAM_DS+str(self.local_port))
    
    def call(self,msg):
        self.logger.info('client send: %s' % str(msg))
        self.command.send_pyobj(msg)
        rsp = self.command.recv_pyobj()
        self.logger.info('client recv: %s' % str(rsp))
        return rsp

    def get(self,key):
        '''
        Lookup the value belonging to the key in the discovery service.
        Wait until the lookup is successful. 
        '''
        ans = None
        tout = 3.0 if Config.DISC_TIMEOUT <= 0 else (Config.DISC_TIMEOUT / 1000.0)
        tslp = 1.0 if Config.RECV_TIMEOUT <= 0 else (Config.RECV_TIMEOUT / 1000.0)
        while True:
            ans = self.call((PeerServer.SLAM_DS_GET,key))
            if ans: break
            time.sleep(tslp)
            tout -= tslp
            if tout <= 0: break
        return ans
    
    def set(self,key,value):
        '''
        Set the value for the key in the discovery service. 
        '''
        return self.call((PeerServer.SLAM_DS_SET,key,value))

  
if __name__ == '__main__':
    '''Test'''
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())


    ctx = zmq.Context.instance()
    disco = DiscoveryService(ctx,'127.0.0.1')
    
    rsp = disco.get('KEY')
    print("disco.get('KEY') -> %s" % rsp)

    rsp = disco.set('KEY','VALUE')
    print("disco.set('KEY','VALUE') -> %s" % rsp)
    
    rsp = disco.get('KEY')
    print("disco.get('KEY') -> %s" % rsp)
    
    disco.stop()
    
#     
    
    