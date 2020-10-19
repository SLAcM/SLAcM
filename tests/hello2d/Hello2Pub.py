'''
Created on Sep 19, 2020

@author: esdev
'''

from slacm.component import Component

class Hello2Pub(Component):
    '''
    classdocs
    '''

    def __init__(self, arg1,arg2=None):
        '''
        Constructor
        '''
        super().__init__()
        self.logger.info('-(%r,%r)' % (arg1,arg2))
        self.cnt = 0
    
    def on_clock(self):
        now = self.clock.recv_pyobj()
        self.logger.info('on_clock(): %s', str(now))
        msg = "msg" + str(self.cnt)
        self.cnt += 1
        self.port.send_pyobj(msg) 
        self.logger.info("send: %s" % msg)
        
        