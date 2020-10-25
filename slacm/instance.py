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
    Class to represent a component instance
    '''
    _modules = {}
    @property
    def modules(self):
        '''
        Dictionary to maintain the loaded modules. 
        '''
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
        Consruct for an instance. Loands the module for the component, constructs the 
        component, and its ports. 
        :param parent: parent actor
        :param model: instance model
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
        '''
        Returns the next port index
        '''
        return next(self.port_index)
    
    def getActor(self):
        '''
        Returns the parent actor object
        '''
        return self.parent
    
    def get_netInfo(self):
        '''
        Returns the network information object
        '''
        return self.netInfo
    
    def is_local(self,message):
        '''
        Returns True if the message is 'host local' for the parent actor. 
        '''
        return self.parent.is_local(message)
    
    def load(self):
        '''
        Load the component implementation code, or retrieve it from the cache.
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
        '''
        Send a command to the component thread
        '''
        self.command.send_pyobj(arg)
        
    def recvResp(self):
        '''
        Receive response from the component thread
        '''
        return self.command.recv_pyobj()
        
    def setup(self):
        '''
        Execute the 'setup' phase of component initialization. Create command socket,
        launch component thread, and instruct it to execute the 'setup'.
        '''
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
        '''
        Executhe the 'finalize' phase of component initialization by instructing
        the component thread. 
        '''
        self.logger.info('Instance.finalize(%s: %s)',self.name,self.type.name)
        self.sendCommand(Component.FINALIZE)
        _ack = self.recvResp()
        
    def start(self):
        '''
        Instruct the component thread to run user code. 
        '''
        self.logger.info('Instance.start(%s: %s)',self.name,self.type.name)
        self.sendCommand(Component.START)
        _ack = self.recvResp()
    
    def stop(self):
        '''
        Instruct the component thread to stop running user code and terminate. 
        '''
        self.logger.info('Instance.stop(%s: %s)',self.name,self.type.name)
        self.sendCommand(Component.STOP)
        _ack = self.recvResp()

    
    
             