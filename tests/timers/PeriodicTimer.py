'''
Created on Sep 19, 2020

@author: esdev
'''

from slacm.component import Component

class PeriodicTimer(Component):
    def __init__(self):
        super(PeriodicTimer, self).__init__()
        
    def on_periodic(self):
        now = self.periodic.recv_pyobj()                # Receive time (as float)
        self.logger.info('on_periodic():%s' % str(now))
        period = self.periodic.getPeriod()              # Query the period
        if period > 1.0:
            period = period - 1.0
        else: 
            period = 5.0
        self.periodic.setPeriod(period)             # Set the period
        self.logger.info('on_periodic(): setting period to %f' % period)
        msg = ('periodic',now)
        self.ticker.send_pyobj(msg)
        
        