'''
Created on Oct 2, 2020

@author: esdev
'''
from slacm.component import Component


class Sensor(Component):
    def __init__(self):
        super().__init__()
        self.logger.info("Sensor()") 
        
    def on_clock(self):
        now = self.clock.recv_pyobj()   # Receive time.time() as float
        self.logger.info('on_clock(): %s' % str(now))
        msg = "data_ready"
        self.ready.send_pyobj(msg) 
    
    def on_request(self):
        req = self.request.recv_pyobj()
        self.logger.info("on_request():%s" % req)
        rep = "sensor_rep"
        self.request.send_pyobj(rep)
