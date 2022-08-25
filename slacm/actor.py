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
    Class for application actors.
    '''
    OK = 0 
    ERR = -1
    
    SETUP = 1
    FINALIZE = 2
    START = 3
    STOP  = 4
    

    def __init__(self, parent, model):
        '''
        :param parent: parent app
        :param model: actor model object
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
        '''
        :return parent: the parent app
        '''
        return self.parent
    
    def get_disco(self):
        '''
        :return disco: the discovery object
        '''
        return self.disco
    
    def get_netInfo(self):
        '''
        :return netInfo: the network interface information 
        '''
        return self.netInfo
    
    def is_local(self,message):
        '''
        Return True if the message is a 'host-local' for the actor.
        '''
        return message in self.locals
    
    def get_comp_params(self,comp):
        '''
        Return the parameters of a component of this actor
        '''
        return self.parent.get_comp_params(self.name,comp)
    
    def setup(self):
        '''
        Execute the 'setup' operation for the actor. 
        Launches a subprocess that runs the components. 
        '''
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
        '''
        Execute the 'finalize' operation for the actor
        '''
        self.logger.info("Actor.finalize")
        self.command.send_pyobj(Actor.FINALIZE)
        _ack = self.command.recv_pyobj()
        
    def run(self):
        '''
        Start running the actor (i.e. its components)
        '''
        self.logger.info("Actor.run")
        self.command.send_pyobj(Actor.START)
        _ack = self.command.recv_pyobj()
    
    def terminate(self):
        '''
        Terminate the actor (i.e. ist components)
        '''
        self.logger.info("Actor.terminate")
        self.command.send_pyobj(Actor.STOP)
        # _ack = self.command.recv_pyobj()    
        
    def join(self):
        '''
        Execute a 'join' operation on the child subprocess. 
        '''
        self.logger.info("Actor.join")
        self.child.join()
    
    def main(self):
        '''
        Main method of the subprocess. Creates the component instances, then launches a
        message handler for commands coming from the parent process.  
        
        '''
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
            
            
            
            
            
        
        
        