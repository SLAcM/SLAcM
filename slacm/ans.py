'''
Created on Sep 18, 2020

@author: esdev
'''

import zmq
from slacm.port import BiPort
from slacm.exceptions import PortOperationError

try:
    import cPickle
    pickle = cPickle
except:
    cPickle = None
    import pickle
    
class AnswerPort(BiPort):
    '''
    Answer port
    '''
    def __init__(self, parent, name, spec):
        super().__init__(parent,name,spec)
        self.logger.info(f'AnswerPort.__init__({name})')
        self.instName = self.parent.name + '.' + self.name
        # parentActor = parentComponent.parent
    
    def setup(self,owner,disco):
        self.owner = owner
        self.socket = self.context.socket(zmq.ROUTER)
        # self.socket.setsockopt(zmq.SNDTIMEO,self.sendTimeout)
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

    def __ans_recv(self,is_pyobj):   
        '''
        Special receive operation for answer ports.
        '''
        try:
            msgFrames = self.socket.recv_multipart()
        except zmq.error.ZMQError as e:
            raise PortOperationError(f"recv error ({e.errno})") from e
        self.__identity = msgFrames[0]                
        if is_pyobj:
            result = pickle.loads(msgFrames[1])     
        else:
            result = msgFrames[1]
        return result
        
    def __ans_send(self,msg,is_pyobj):
        '''
        Special send operation for answer ports. 
        '''
        try:
            sendMsg = [self.__identity]
            if is_pyobj:
                payload = zmq.Frame(pickle.dumps(msg)) 
            else:
                payload = zmq.Frame(msg)                     
            sendMsg += [payload]
            self.socket.send_multipart(sendMsg)
        except zmq.error.ZMQError as e:
            raise PortOperationError(f"send error ({e.errno})") from e
        return True

    def get_identity(self):
        '''
        Retrieve identity of the sender of last message received 
        '''
        return self.__identity
    
    def set_identity(self,identity):
        '''
        Set the identity of the send target. (i.e. address)
        '''
        self.__identity = identity
        
    def recv_pyobj(self):
        return self.__ans_recv(True)

    def send_pyobj(self,msg):
        return self.__ans_send(msg,True)

    def recv(self):
        return self.__ans_recv(False)

    def send(self,msg):
        return self.__ans_send(msg,False)
    
    

    
    