'''
Created on Sep 19, 2020

@author: esdev
'''

from slacm.component import Component

class HelloAnswer(Component):
    '''
    classdocs
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super().__init__()
        self.queue = []
    
    def on_port(self):
        msg = self.port.recv_pyobj()
        self.logger.info('on_port(): recv = %s', msg)
        recent = (self.port.get_identity(),msg)
        if len(self.queue) > 0:
            (identity,message) = self.queue.pop(0)
            self.port.set_identity(identity)
            self.port.send_pyobj(message)
        self.queue.append(recent)
        
        
        
        