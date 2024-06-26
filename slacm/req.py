'''
Created on Sep 18, 2020

@author: esdev
'''
import zmq
import logging
from slacm.port import BiPort

class RequestPort(BiPort):
    '''
    Request port
    '''
    def __init__(self, parent, name, spec):
        super().__init__(parent,name,spec)
        self.logger.info('RequestPort.__init__(%s)',name)
        self.instName = self.parent.name + '.' + self.name
        # parentActor = parentComponent.parent
    
    def setup(self,owner,disco):
        self.owner = owner
        self.socket = self.context.socket(zmq.REQ)
        # self.socket.setsockopt(zmq.SNDTIMEO,self.sendTimeout) 
        # self.soecket.setsockopt(zmq.RCVTIMEO,self.recvTimeout)
        if not self.isLocalPort:
            self.host = self.netInfo.globalHost
        else:
            self.host = self.netInfo.localHost

    def finalize(self,disco):
        key = self.formKey()
        value = disco.get(key)
        if value is not None:
            endPoint = "tcp://" + value
            self.socket.connect(endPoint)
        else:
            self.logger.warning('RequestPort.finalize() %s - source port lookup failed' % self.instName)
        
    def inSocket(self):
        return True
    
    
    
    
    