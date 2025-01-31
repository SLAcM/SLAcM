'''
Created on Sep 18, 2020

@author: esdev
'''
import zmq
import logging

from slacm.port import UniPort
from slacm.exceptions import PortOperationError

class SubscriberPort(UniPort):
    '''
    Subscriber port
    '''
    def __init__(self, parent, name, spec):
        super().__init__(parent,name,spec)
        self.logger.info('SubscriberPort.__init__(%s)',name)
        self.instName = self.parent.name + '.' + self.name
        # parentActor = parentComponent.parent
    
    def setup(self,owner,disco):
        self.owner = owner
        self.socket = self.context.socket(zmq.SUB)
        self.socket.setsockopt_string(zmq.SUBSCRIBE, '')
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
            self.logger.warning(f'SubscriberPort.finalize() {self.instName}: source port lookup failed')
                
    def inSocket(self):
        return True

    def send_pyobj(self,msg):
        raise PortOperationError("attempt to send_pyobj() through a subscriber port")
    
    def send(self,msg):
        raise PortOperationError("attempt to send() through a subscriber port")