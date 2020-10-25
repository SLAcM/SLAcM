'''
Created on Sep 18, 2020

@author: esdev
'''
import zmq
from slacm.port import BiPort

class ReplyPort(BiPort):
    '''
    Reply port
    '''
    def __init__(self, parent, name, spec):
        super().__init__(parent,name,spec)
        self.logger.info('ReplyPort.__init__(%s)',name)
        self.instName = self.parent.name + '.' + self.name
        # parentActor = parentComponent.parent
    
    def setup(self,owner,disco):
        self.owner = owner
        self.socket = self.context.socket(zmq.REP)
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
        return True

    
    
    
    