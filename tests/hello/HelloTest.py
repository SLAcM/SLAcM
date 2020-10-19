'''
Created on Sep 19, 2020

@author: esdev
'''

from slacm.component import Component

class HelloTest(Component):
    '''
    classdocs
    '''

    def __init__(self):
        '''
        Constructor
        '''
        super().__init__()
    
    def on_clock(self):
        now = self.clock.recv_pyobj()
        self.logger.info('on_clock(): %s', str(now))
        
        