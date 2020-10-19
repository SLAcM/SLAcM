'''
Created on Sep 19, 2020

@author: esdev
'''

from slacm.component import Component

class Hello2Sub(Component):
    '''
    classdocs
    '''

    def __init__(self, arg3, arg4):
        '''
        Constructor
        '''
        super().__init__()
        self.logger.info('-(%r,%r)' % (arg3,arg4))
    
    def on_port(self):
        msg = self.port.recv_pyobj()
        self.logger.info('on_port(): recv = %s', msg)
        
        
        
        