'''
Created on Sep 19, 2020

@author: esdev
'''

from slacm.component import Component

class SporadicTimer(Component):
    def __init__(self):
        super(SporadicTimer, self).__init__()
        
    def on_sporadic(self):
        now = self.sporadic.recv_pyobj()            # Receive time (as float)
        self.logger.info("on_sporadic() %s" % str(now))
        delay = self.sporadic.getDelay()
        if delay > 1.0:         # If delay > 1.0
            delay = delay - 1.0
        else:
            delay = 4.0
        self.logger.info('on_sporadic(): setting delay to %f' % delay)
        self.sporadic.setDelay(delay)           # Change delay
        self.sporadic.launch()                  # Launch it again
        
    def on_ticker(self):
        now = self.ticker.recv_pyobj()              # Receive message
        self.logger.info('on_ticker():%s' % str(now))
        if self.sporadic.running():
            self.logger.info("on_ticker(): canceling sporadic")
            self.sporadic.cancel()
        delay = 4.0
        self.logger.info('on_ticker: setting delay to %f' % delay)
        self.sporadic.setDelay(delay)           # Change delay to 4.0
        self.sporadic.launch()                  # Launch the sproadic timer