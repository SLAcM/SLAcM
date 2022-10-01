'''
Test and example for using the Python 'transitions' package 
See documentation for the package at https://github.com/pytransitions/transitions 
Created on Sep 19, 2020

@author: esdev
'''

from slacm.component import Component
from transitions import Machine
from transitions.extensions import LockedMachine
from transitions.extensions.states import add_state_features,Timeout

@add_state_features(Timeout)
class TimeoutMachine(LockedMachine):
    '''
    Extended LockedMachine with Timeout capability. 
    If timeouts are not used, the base Machine should be used.
    If timeouts are used, their callbacks are executed in an another ephemeral 'Timer' thread. 
    As the machine can be manipulated by its parent component, it is necessary to use a 'LockedMachine'.     
    '''
    pass

class FSMObject(object):
    '''
    Example FSMObject that holds the machine.
    The parent component can trigger the transitions of the machine, query its state, etc. 
    Callbacks of the machine must NOT call any operation on the parent component, except firing 
    a timer port that handles a timeout (if they are used).  
    '''
    def __init__(self,parent,tport):
        '''
        :param parent : component object that owns this FSM
        :param tport : a timer port object of the parent component that is 'fired'when the timeout happens 
        '''
        self.parent = parent
        self.tport = tport
        # Example state machine with 3 states, the states 'waiting' and 'running' with timeout.  
        self.states = [ {'name' : 'init' }, # Initial state
                        {'name' : 'waiting', 'timeout' : 3.0, 'on_timeout' : 'ready'}, 
                        {'name' : 'running', 'timeout' : 4.0, 'on_timeout' : 'block'}] 
        # Transitions: 
        # go() is fired by the parent component, ready() and block() are fired when a timeout happens
        # These transitions also activate a callback that fires the timer port 
        self.transitions = [{'trigger' : 'go', 'source' : 'init', 'dest' : 'waiting' },
                            {'trigger' : 'ready', 'source' : 'waiting', 'dest' : 'running', 'before': 'fire_trigger'},
                            {'trigger' : 'block', 'source' : 'running', 'dest' : 'waiting', 'before': 'fire_trigger'}]
        # Instantiate the machine
        self.machine = TimeoutMachine(model=self, states = self.states, transitions = self.transitions, initial= 'init')
        self.parent.logger.info('FSMSObject initialized')
        
    def fire_trigger(self):
        '''
        Calls fire() method on the timer port of the parent component.
        Such callbacks must NOT perform any other operation on the parent component. 
        '''
        self.parent.logger.info('fire_trigger')
        self.tport.fire()
    
class FSMTest(Component):
    '''
    FSM Test component
    '''
    def __init__(self):
        '''
        Constructor
        '''
        super().__init__()
        self.logger.info('init done')
        self.fsm = None
        
    def activate(self):
        '''
        Create the FSMObject in the current (component) thread
        '''
        self.logger.info('activate')
        self.fsm = FSMObject(self,self.trigger)
 
    def on_trigger(self):
        '''
        Print a message when the 'trigger' (timer port handling the state machine's timeout) is fired
        '''      
        now = self.trigger.recv_pyobj()
        self.logger.info('on_trigger(): %s', str(now))
    
    def on_ticker(self):
        '''
        Handler for the periodic ticker, on the first call it starts the state machine
        '''
        now = self.ticker.recv_pyobj()
        state = self.fsm.state
        self.logger.info('on_ticker(): %s -> %r', str(now), state)
        if state == 'init' : self.fsm.go()
        
        
        