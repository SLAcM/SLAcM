'''
Created on Sep 18, 2020

@author: esdev
'''
import threading
import zmq
import time
import logging
import struct
from enum import Enum,auto

from slacm.port import Port
from slacm.exceptions import InvalidOperation

class TimerThread(threading.Thread):
    '''
    Thread for a timer port. 
    '''
    class Command(Enum):        # Timer command codes
        TERMINATE   = auto()            
        ACTIVATE    = auto()          
        DEACTIVATE  = auto()            
        START       = auto()           
        CANCEL      = auto()
        HALT        = auto()
        
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
        self._ready = threading.Event()         # Timer thread ready to accept commands
        self._ready.clear()
        self._running = False                   # Timer ('counter') is running
        self.lock = None
        
        
    def ready(self):
        return self._ready
    
    def cmdError(self,where,cmd):
        self.logger.error("Timer %s:%s: cmd = %r" % (self.name,where,cmd))
    
    def waitFor(self,timeout=None):
        res = self.poller.poll(timeout)
        if len(res) == 0:
            return None
        else:          
            (s,_m) = res[0]
            with self.lock:
                data = s.recv_pyobj()
            return data
        
    def run(self):
        self.logger.info("TimerThread.run(%s)",self.name)
        self.lock = threading.RLock()
        self.socket = self.context.socket(zmq.PAIR) # PUB
        self.socket.bind('inproc://timer_' + self.name)   
        self.poller = zmq.Poller()
        self.poller.register(self.socket,zmq.POLLIN)
        self._ready.set()                       # Ready to accept commands
        self.timeout = None
        self.active = False
        self._running = False
        self.skip = False
        self.last = None        

        while 1:
            msg = self.waitFor(self.timeout)
            if msg == TimerThread.Command.TERMINATE: break  # Terminated
            elif msg == None:                               # Timeout
                if not self.active:                         # Wait if not active
                    self.timeout = None
                    continue
                self.last = time.time()
                if self._running:
                    if self.periodic and self.skip:
                        self.skip = False
                    else:
                        with self.lock:
                            self.socket.send_pyobj(self.last)          
                if self.periodic:           # Periodic: again
                    self.timeout = int(self.period * 1000)
                    pass                              
                else:                       # Sporadic: wait for next command
                    self._running = False
                    self.timeout = None
                continue
            elif msg == TimerThread.Command.ACTIVATE:
                self.active = True
                self.last = None
            elif msg == TimerThread.Command.DEACTIVATE:
                self.active = False
                self.timeout = None
                self.last = None
            elif msg == TimerThread.Command.START:
                if self.active: 
                    if self.periodic:
                        self.timeout = int(self.period * 1000)
                    else:
                        self.timeout = int(self.delay * 1000)
                    self._running = True
                else:                           # Not active 
                    self.cmdError('not active',msg)
                    continue
            elif msg == TimerThread.Command.CANCEL:
                if self.periodic:
                    if self.last != None:       # Skip next firing
                        delay = self.last + self.period - time.time()
                        self.timeout = int(delay * 1000) 
                        self.skip = True
                else:
                    self._running = False
                    self.timeout = None
            elif msg == TimerThread.Command.HALT:
                self.timeout = None
                self._running = False
            else:
                self.cmdError('loop',msg)
        self.logger.info("TimerThread.done")
            
    def fire(self):
        '''
        Fire timer from the 'outside'
        '''
        if self.active:
            with self.lock:
                self.last = time.time()
                self.socket.send_pyobj(self.last)
            
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
        
    
    def running(self):
        '''
        Returns True if the timer is running
        '''
        return self._running
        
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
            self.socket.send_pyobj(TimerThread.Command.ACTIVATE)
            if self.thread.getPeriod():             # Periodic timer
                self.socket.send_pyobj(TimerThread.Command.START)
        
    def deactivate(self):
        '''
        Deactivate the timer port
        '''
        if self.thread != None:
            self.socket.send_pyobj(TimerThread.Command.DEACTIVATE)
        
    def terminate(self):
        '''
        Terminate the timer 
        '''
        if self.thread != None:
            self.logger.info("terminating")
            self.socket.send_pyobj(TimerThread.Command.TERMINATE)
            # self.thread.terminate()
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
            raise InvalidOperation(f"invalid argument: setPeriod({_period})")
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
            raise InvalidOperation(f"invalid argument: setDelay({_delay})")
        if self.thread != None: 
            self.thread.setDelay(_delay)
        
    def launch(self):
        '''
        Launch (start) the sporadic timer
        '''
        if self.thread != None: 
            # self.thread.launch()
            self.socket.send_pyobj(TimerThread.Command.START)

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
            # self.thread.cancel()
            self.socket.send_pyobj(TimerThread.Command.CANCEL)
    
    def halt(self):
        '''
        Halt the timer
        '''
        if self.thread != None: 
            # self.thread.halt()
            self.socket.send_pyobj(TimerThread.Command.HALT)
            
    def fire(self):
        ''' 
        Force a timer firing
        '''
        if self.thread != None:
            self.thread.fire() 
        
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
    
    