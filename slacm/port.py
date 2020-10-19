'''
Created on Sep 18, 2020

@author: esdev
'''

import zmq
import logging
from slacm.exceptions import UndefinedOperation,PortOperationError

try:
    import cPickle
    pickle = cPickle
except:
    cPickle = None
    import pickle

class Port(object):

    def __init__(self, parent, name, spec=None):
        '''
        Constructor
        '''
        self.logger = logging.getLogger(__name__)
        self.parent = parent
        self.name = name
        self.spec = spec
        self.index = self.parent.get_next_index()
        self.context = parent.context
        self.netInfo = parent.get_netInfo()
        self.socket = None
        self.owner = None
        self.portNum = -1
        self.host = None
    
    def is_msg_local(self):
        raise UndefinedOperation('Port.is_msg_local')
        
    def getIndex(self):
        return self.index
        
    def setup(self,owner,disco):
        raise UndefinedOperation('Port.setup')
    
    def finalize(self,disco):
        raise UndefinedOperation('Port.finalize')
    
    def getSocket(self):
        return self.socket
        
    def inSocket(self):
        raise UndefinedOperation('Port.inSocket')
    
    def activate(self):
        pass
        
    def deactivate(self):
        pass
    
    def terminate(self):
        pass
    
    def send_pyobj(self,msg):
        try:
            result = self.socket.send_pyobj(msg)
        except zmq.error.ZMQError as e:
            raise PortOperationError("recv error (%d)" % e.errno) from e
        return result
    
    def recv_pyobj(self):
        try:
            result = self.socket.recv_pyobj()
        except zmq.error.ZMQError as e:
            raise PortOperationError("recv error (%d)" % e.errno) from e
        return result

    def send(self,msg):
        try:
            result = self.socket.send(msg)
        except zmq.error.ZMQError as e:
            raise PortOperationError("recv error (%d)" % e.errno) from e
        return result
    
    def recv(self):
        try:
            result = self.socket.recv()
        except zmq.error.ZMQError as e:
            raise PortOperationError("recv error (%d)" % e.errno) from e
        return result
    
    def formKey(self):
        raise UndefinedOperation('Port.inSocket')
    
    def formValue(self):
        return '%s:%d' % (self.host,self.portNum)

class UniPort(Port):
    def __init__(self, parent, name, spec=None):
        super().__init__(parent,name,spec)
        self.isLocalPort = self.is_msg_local()

    def is_msg_local(self):
        return self.parent.is_local(self.spec.type)
    
    def formKey(self):
        return self.spec.type.name + (('@' +  self.netInfo.macAddress) if self.isLocalPort else '')
        
class BiPort(Port):
    def __init__(self, parent, name, spec=None):
        super().__init__(parent,name,spec)
        self.isLocalPort = self.is_msg_local()
                
    def is_msg_local(self):
        return self.parent.is_local(self.spec.req_type) and \
            self.parent.is_local(self.spec.rep_type)
        
    def formKey(self):
        return self.spec.req_type.name + '#' + self.spec.rep_type.name +  \
                    (('@' + self.netInfo.macAddress) if self.isLocalPort else '')
