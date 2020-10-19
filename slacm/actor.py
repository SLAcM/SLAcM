'''
Created on Sep 18, 2020

@author: esdev
'''

import os,signal
import logging
import zmq
import traceback
from multiprocessing import Process
import time

from slacm.instance import Instance

class Actor(object):
    '''
    classdocs
    '''
    OK = 0 
    ERR = -1
    
    SETUP = 1
    FINALIZE = 2
    START = 3
    STOP  = 4
    

    def __init__(self, parent, model):
        '''
        Constructor
        '''
        self.logger = logging.getLogger(__name__)
        self.parent = parent
        self.model = model
        self.name = model.name
        self.parentContext = self.parent.context
        self.childContext = None
        self.logger.info('Actor.__init__:%s',self.name)
        self.instances = {}
        self.disco = self.parent.get_disco()
        self.netInfo = self.parent.get_netInfo()
        self.locals = self.model.locals
        self.params = self.parent.get_actor_params(self.name)
        
    def getApp(self):
        return self.parent
    
    def get_disco(self):
        return self.disco
    
    def get_netInfo(self):
        return self.netInfo
    
    def is_local(self,message):
        return message in self.locals
    
    def get_comp_params(self,comp):
        return self.parent.get_comp_params(self.name,comp)
    
    def setup(self):
        self.logger.info("Actor.setup")
        self.command = self.parentContext.socket(zmq.PAIR)
        self.parentPort = self.command.bind_to_random_port("tcp://" + self.netInfo.localHost) 
        self.child = Process(target=self.main) # ,args=(self,))
        self.child.daemon = True
        self.child.start()
        time.sleep(0.001)
        self.command.send_pyobj(Actor.SETUP)
        _ack = self.command.recv_pyobj()    

    def finalize(self):
        self.logger.info("Actor.finalize")
        self.command.send_pyobj(Actor.FINALIZE)
        _ack = self.command.recv_pyobj()
        
    def run(self):
        self.logger.info("Actor.run")
        self.command.send_pyobj(Actor.START)
        _ack = self.command.recv_pyobj()
    
    def terminate(self):
        self.logger.info("Actor.terminate")
        self.command.send_pyobj(Actor.STOP)
        _ack = self.command.recv_pyobj()
        
    def join(self):
        self.logger.info("Actor.join")
        self.child.join()
    
    def main(self):
        self.childContext = zmq.Context()
        self.control = self.childContext.socket(zmq.PAIR)
        self.control.connect("tcp://" + self.parent.netInfo.localHost + ":" + str(self.parentPort))
        time.sleep(0.001)
        
        signal.signal(signal.SIGTERM,signal.SIG_IGN)
        signal.signal(signal.SIGINT,signal.SIG_IGN)
        
        try:
            for instance in self.model.instances:
                self.instances[instance.name] = Instance(self,instance)
        except Exception as e:
            traceback.print_exc()
            return
            
        while True:
            msg = self.control.recv_pyobj()
            self.logger.info("main: cmd: %s" % str(msg))
            if msg == Actor.SETUP:
                for (_name, instance) in self.instances.items():
                    instance.setup()
                self.control.send_pyobj(Actor.OK)
            elif msg == Actor.FINALIZE:
                for (_name, instance) in self.instances.items():
                    instance.finalize()
                self.control.send_pyobj(Actor.OK)
            elif msg == Actor.START:
                for (_name, instance) in self.instances.items():
                    instance.start()
                self.control.send_pyobj(Actor.OK)
            elif msg == Actor.STOP:
                for (_name, instance) in self.instances.items():
                    instance.stop()
                self.control.send_pyobj(Actor.OK)
                break
            
            
            
            
            
        
        
        