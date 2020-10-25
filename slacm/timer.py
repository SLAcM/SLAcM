'''
Created on Sep 18, 2020

@author: esdev
'''
import threading
import zmq
import time
import logging
import struct

from slacm.port import Port
from slacm.exceptions import InvalidOperation

class TimerThread(threading.Thread):
    '''
    Thread for a timer port. 
    '''
    def __init__(self,parent):
        threading.Thread.__init__(self)
        self.logger = logging.getLogger(__name__)
        self.name = parent.instName
        self.logger.info("TimerThread.__init__(%s)",self.name)
        self.context = parent.context
        if parent.period == 0:
            self.period = None
            self.periodic = False
        else:
            self.period = parent.period * 0.001 # millisec
            self.periodic = True
        self.delay = None
        self.active = threading.Event()
        self.active.clear()
        self.waiting = threading.Event()
        self.waiting.clear()
        self.terminated = threading.Event()
        self.terminated.clear()
        self.started = threading.Event()
        self.started.clear()
        
    def run(self):
        self.logger.info("TimerThread.run(%s)",self.name)
        self.socket = self.context.socket(zmq.PAIR) # PUB
        self.socket.bind('inproc://timer_' + self.name)   
        while 1:
            self.active.wait(None)                  # Wait for activation
            if self.terminated.is_set(): break      # If terminated, we exit
            if self.periodic:                       # Periodic timer
                self.started.wait(None)  
                if self.terminated.is_set(): break        
                self.waiting.wait(self.period)      # Wait for period
                if self.terminated.is_set(): break  
                if self.waiting.is_set():           # Period was cancelled
                    self.waiting.clear()            # Start next period, but do not send tick
                    continue
                if self.active.is_set() and self.started.is_set():            # Send tick (if active)
                    value = time.time()
                    self.socket.send_pyobj(value)
            else:                                   # One shot timer
                while 1:
                    if self.terminated.is_set() : break  
                    self.started.wait(None)         # Wait for start
                    if self.terminated.is_set(): break
                    assert self.delay != None and self.delay > 0.0
                    self.waiting.wait(self.delay)   # Wait for the delay
                    if self.terminated.is_set() : break  
                    self.started.clear()            # We are not started anymore
                    if self.waiting.is_set():       # Delay was cancelled
                        self.waiting.clear()        # Enable next waiting, but  do not send tick
                        continue
                    if self.active.is_set():        # Send tick (if active)
                        value = time.time()
                        self.socket.send_pyobj(value)
                break
        self.logger.info("TimerThread.done")
            
    def activate(self):
        '''
        Activate the timer port
        '''
        self.logger.info("TimerThread.activate()")
        self.active.set()
        if self.periodic:
            self.started.set()
    
    def deactivate(self):
        '''
        Deactivate the timer port
        '''
        self.logger.info("TimerThread.deactivate()")
        self.active.clear()
    
    def terminate(self):
        '''
        Terminate the timer 
        '''
        self.logger.info("TimerThread.terminate()")
        self.terminated.set()
        self.started.set()          # Get out of wait if we are not started
        self.waiting.set()

    
    def getPeriod(self):
        ''' 
        Read out the period
        '''
        return self.period
    
    def setPeriod(self,_period):
        ''' 
        Set the period - will be changed after the next firing.
        Period must be positive
        '''
        assert type(_period) == float and _period > 0.0  
        self.period = _period
    
    def getDelay(self):
        '''
        Get the current delay (for sporadic timer)
        '''
        return self.delay
    
    def setDelay(self,_delay):
        '''
        Set the current delay (for sporadic timer)
        '''
        assert type(_delay) == float and _delay > 0.0  
        self.delay = _delay
        
    def launch(self):
        '''
        Launch (start) the sporadic timer
        '''
        self.started.set()
    
    def running(self):
        '''
        Returns True if the timer is running
        '''
        return self.started.is_set()
    
    def cancel(self):
        '''
        Cancel the sporadic timer
        '''
        if self.started.is_set():
            self.waiting.set()      # Go to wait mode if started
        else:
            pass                    # Ignore if not started
        
    def halt(self):
        '''
        Halt the timer
        '''
        self.started.clear()
        
class TimerPort(Port):
    '''
    Timer port
    '''

    def __init__(self, parent, name, spec):
        '''
        Constructor for a Timer port. 
        '''
        super().__init__(parent,name,spec)
        self.logger = logging.getLogger(__name__)
        self.logger.info('TimerPort.__init__(%s)',name)
        self.instName = self.parent.name + '.' + self.name
        self.context = parent.context
        self.period = self.spec.period
        self.thread = None

    def setup(self,owner,_disco):
        self.owner = owner
        self.thread = TimerThread(self)
        self.thread.start() 
        time.sleep(0.001)
        assert self.instName == self.thread.name       
        self.socket = self.context.socket(zmq.PAIR) # SUB
        self.socket.connect('inproc://timer_' + self.instName)

    def finalize(self,_disco):
        pass
    
    def reset(self):
        pass
    
    def activate(self):
        '''
        Activate the timer port
        '''
        if self.thread != None:
            self.thread.activate()
        
    def deactivate(self):
        '''
        Deactivate the timer port
        '''
        if self.thread != None:
            self.thread.deactivate()
        
    def terminate(self):
        '''
        Terminate the timer 
        '''
        if self.thread != None:
            self.logger.info("terminating")
            # self.thread.halt()
            self.thread.terminate()
            self.thread.join()
            self.logger.info("terminated")

    def getPeriod(self):
        ''' 
        Read the period of the periodic timer
        '''
        if self.thread != None:
            return self.thread.getPeriod()
        else:
            return None
    
    def setPeriod(self,_period):
        ''' 
        Set the period - will be changed after the next firing.
        Period must be positive
        '''
        if not (type(_period) == float and _period > 0.0):
            raise InvalidOperation("invalid argument %s" % str(_period))
        if self.thread != None: 
            self.thread.setPeriod(_period)
    
    def getDelay(self):
        '''
        Get the current delay (for sporadic timer)
        '''
        if self.thread != None: 
            return self.thread.getDelay()
        else:
            return None
    
    def setDelay(self,_delay):
        '''
        Set the current delay (for sporadic timer)
        '''
        if not (type(_delay) == float and _delay > 0.0):
            raise InvalidOperation("invalid argument %s" % str(_delay))
        if self.thread != None: 
            self.thread.setDelay(_delay)
        
    def launch(self):
        '''
        Launch (start) the sporadic timer
        '''
        if self.thread != None: 
            self.thread.launch()

    def running(self):
        '''
        Returns True if the timer is running
        '''
        if self.thread != None:
            return self.thread.running()
        else:
            return None

    def cancel(self):
        '''
        Cancel the sporadic timer
        '''
        if self.thread != None: 
            self.thread.cancel()
    
    def halt(self):
        '''
        Halt the timer
        '''
        if self.thread != None: 
            self.thread.halt()

    def getSocket(self):
        return self.socket
    
    def inSocket(self):
        return True
    
    def recv_pyobj(self):
        res = self.socket.recv_pyobj()
        return res
    
    def recv(self):
        value = self.socket.recv_pyobj()
        res = bytearray(struct.pack("f", value))
        return res
    
    def send_pyobj(self,msg):
        raise InvalidOperation("attempt to send_pyobj() through a timer port")
    
    def send(self,msg):
        raise InvalidOperation("attempt to send() through a timer port")
    
    