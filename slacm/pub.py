'''
Created on Sep 18, 2020

@author: esdev
'''
import zmq
import logging

from slacm.port import UniPort
from slacm.exceptions import PortOperationError

class PublisherPort(UniPort):

    def __init__(self, parent, name, spec):
        '''
        Constructor
        '''
        super().__init__(parent,name,spec)
        self.logger.info('PublisherPort.__init__(%s)',name)
        self.instName = self.parent.name + '.' + self.name
        # parentActor = parentComponent.parent
    
    def setup(self,owner,disco):
        self.owner = owner
        self.socket = self.context.socket(zmq.PUB)
        # self.socket.setsockopt(zmq.SNDTIMEO,self.sendTimeout) 
        self.portNum = -1
        if not self.isLocalPort:
            self.portNum = self.socket.bind_to_random_port("tcp://" + self.netInfo.globalHost)
            self.host = self.netInfo.globalHost
        else:
            self.portNum = self.socket.bind_to_random_port("tcp://" + self.netInfo.localHost)
            self.host = self.netInfo.localHost
        key,value = self.formKey(),self.formValue()
        disco.set(key,value)

    def finalize(self,disco):
        pass
    
    def inSocket(self):
        return False

    def recv_pyobj(self):
        raise PortOperationError("attempt to recv_pyobj() through a publisher port")
    
    def recv(self):
        raise PortOperationError("attempt to recv() through a publisher port")
    