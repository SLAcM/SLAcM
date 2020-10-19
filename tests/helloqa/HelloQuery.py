'''
Created on Sep 19, 2020

@author: esdev
'''

from slacm.component import Component

class HelloQuery(Component):
    '''
    classdocs
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super().__init__()
        self.id = id(self)
        self.cnt = 0
    
    def on_clock(self):
        now = self.clock.recv_pyobj()
        self.logger.info('[%d]on_clock(): %s', self.id, str(now))
        msg = "msg.%d.%d" % (self.id,  self.cnt)
        self.cnt += 1
        self.port.send_pyobj(msg) 
        self.logger.info("[%d]send: %s", self.id, msg)
        
    def on_port(self):
        rsp = self.port.recv_pyobj()
        self.logger.info("[%d]recv: %s", self.id, rsp)
        
        
        