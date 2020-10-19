'''
Created on Sep 19, 2020

@author: esdev
'''

import time
import zmq
import logging
import importlib
from itertools import count

from slacm.exceptions import LoadError
from slacm.timer import TimerPort
from slacm.pub import PublisherPort
from slacm.sub import SubscriberPort
from slacm.req import RequestPort
from slacm.rep import ReplyPort
from slacm.qry import QueryPort
from slacm.ans import AnswerPort
from slacm.component import Component,ComponentThread

class Instance(object):
    '''
    classdocs
    '''
    _modules = {}
    @property
    def modules(self):
        return self._modules
    @modules.setter
    def modules(self,val):
        self._modules = val
        
    _portTypes = {
        "PubPort" : PublisherPort,
        "SubPort" : SubscriberPort,
        "ReqPort" : RequestPort,
        "RepPort" : ReplyPort,
        "QryPort" : QueryPort,
        "AnsPort" : AnswerPort,
        "TimPort" : TimerPort
        }
        
    def __init__(self, parent, model):
        '''
        Constructor
        '''
        self.logger = logging.getLogger(__name__)
        
        self.parent = parent
        self.name = model.name
        self.type = model.type
        self.context = parent.childContext
        self.disco = self.parent.get_disco()
        self.netInfo = self.parent.get_netInfo()
        self.typeName = self.type.name
        self.params = self.parent.get_comp_params(self.name)
        self.args = self.params if self.params else {} 
        self.qualName = '%s.%s.%s' % (self.parent.name,self.name,self.typeName)
        self.logger.info('Instance.__init__(%s)',self.qualName)
        self.load()
        self.class_ = getattr(self.module_, self.typeName)
        self.class_.OWNER = self            # Trick to set the OWNER of the component 
        self.component = self.class_(**self.args)    # Run the component constructor
        self.class_.OWNER = None
        self.thread = None
        self.ports = {}
        self.port_index = count(0)
        for port in self.type.ports:
            _class = self._portTypes[port.__class__.__name__]
            self.ports[port.name] = _class(self,port.name,port)
            setattr(self.component,port.name,self.ports[port.name]) 
    
    def get_next_index(self):
        return next(self.port_index)
    
    def getActor(self):
        return self.parent
    
    def get_netInfo(self):
        return self.netInfo
    
    def is_local(self,message):
        return self.parent.is_local(message)
    
    def load(self):
        '''
        Load the component implementation code
        '''
        if self.typeName not in self.modules:
            try:
                self.module_ = importlib.import_module(self.typeName)
                self.modules[self.typeName] = self.module_ 
            except Exception as e:
                raise LoadError ("%s: %s" % (type(e),e))
        else:
            self.module_ = self.modules[self.typeName]
    
    def sendCommand(self,arg):
        self.command.send_pyobj(arg)
        
    def recvResp(self):
        return self.command.recv_pyobj()
        
    def setup(self):
        self.logger.info('Instance.setup(%s: %s)',self.name,self.type.name)
        self.context = self.parent.childContext
        self.command = self.context.socket(zmq.PAIR)
        self.command.bind("inproc://part_" + self.name + '_control')
        self.thread = ComponentThread(self)
        self.thread.daemon = True
        self.thread.start()
        time.sleep(0.001)
        self.sendCommand(Component.SETUP)
        _ack = self.recvResp()
    
    def finalize(self):
        self.logger.info('Instance.finalize(%s: %s)',self.name,self.type.name)
        self.sendCommand(Component.FINALIZE)
        _ack = self.recvResp()
        
    def start(self):
        self.logger.info('Instance.start(%s: %s)',self.name,self.type.name)
        self.sendCommand(Component.START)
        _ack = self.recvResp()
    
    def stop(self):
        self.logger.info('Instance.stop(%s: %s)',self.name,self.type.name)
        self.sendCommand(Component.STOP)
        _ack = self.recvResp()

    
    
             