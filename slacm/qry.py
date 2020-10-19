'''
Created on Sep 18, 2020

@author: esdev
'''
import zmq
from slacm.port import BiPort

class QueryPort(BiPort):
    def __init__(self, parent, name, spec):
        '''
        Constructor
        '''
        super().__init__(parent,name,spec)
        self.logger.info('QueryPort.__init__(%s)',name)
        self.instName = self.parent.name + '.' + self.name
        # parentActor = parentComponent.parent
    
    def setup(self,owner,disco):
        self.owner = owner
        self.socket = self.context.socket(zmq.DEALER)
        macAddress = self.netInfo.macAddress
        self.__identity = '%s.%s' % (str(macAddress),str(id(self)))
        self.socket.setsockopt_string(zmq.IDENTITY, self.__identity, 'utf-8')
        # self.socket.setsockopt(zmq.SNDTIMEO,self.sendTimeout)
        # self.socket.setsockopt(zmq.RCVTIMEO,self.recvTimeout)
        if not self.isLocalPort:
            self.host = self.netInfo.globalHost
        else:
            self.host = self.netInfo.localHost
        
    def finalize(self,disco):
        key = self.formKey()
        value = disco.get(key)
        endPoint = "tcp://" + value
        self.socket.connect(endPoint)
        
    def inSocket(self):
        return True

    
    
    
    