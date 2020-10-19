'''
Created on Sep 19, 2020

@author: esdev
'''
import threading
import zmq
import time
import logging
import heapq
import itertools
import traceback
import pathlib
from ruamel.yaml import YAML
from slacm.discovery import DiscoveryClient
from slacm.exceptions import UndefinedHandler
from slacm.config import Config,HostnameFilter

class ComponentThread(threading.Thread):
    def __init__(self,parent):
        threading.Thread.__init__(self)
        self.logger = logging.getLogger(__name__)
        self.logger.info("ComponentThread.__init__(%s)",self.name)
        self.parent = parent
        _app = self.parent.getActor().getApp()
        self.name = parent.name
        self.context = parent.context
        self.disco_service = parent.disco
        self.disco_client = None
        self.component = parent.component
        self.netInfo = self.parent.get_netInfo()
        self.handlers = {}
        self.control = None
        self.pq = []
        self.tc = itertools.count()
    
    def get_netInfo(self):
        return self.netInfo
    
    def setupControl(self):
        self.control = self.context.socket(zmq.PAIR)
        self.control.connect('inproc://part_' + self.name + '_control')
    
    def sendControl(self,msg):
        self.logger.info('sendControl[%s]: %s', self.name,str(msg))
        self.control.send_pyobj(msg)
        
    def recvControl(self):
        msg = self.control.recv_pyobj()
        self.logger.info('recvControl[%s]: %s', self.name,str(msg))
        return msg
    
    def setupPoller(self):
        self.poller  = zmq.Poller()
        self.sock2NameMap = {}
        self.sock2PortMap = {}
        self.poller.register(self.control,zmq.POLLIN)
        self.sock2NameMap[self.control] = ""
        self.sock2PrioMap = {}
        
    def updatePoller(self):
        for portName in self.parent.ports:
            portObj = self.parent.ports[portName]
            portSocket = portObj.getSocket()
            portIsInput = portObj.inSocket()
            if portSocket != None:
                self.sock2PortMap[portSocket] = portObj
                if portIsInput:
                    self.poller.register(portSocket,zmq.POLLIN)
                    self.sock2NameMap[portSocket] = portName
                    self.sock2PrioMap[portSocket] = portObj.getIndex()
                    
    def setupDisco(self):
        self.disco_client = DiscoveryClient(self.context,self.disco_service)

    
    def setup(self):
        for (_portName,port) in self.parent.ports.items():
            _res = port.setup(self,self.disco_client)
            
    def finalize(self):
        for (_portName,port) in self.parent.ports.items():
            _res = port.finalize(self.disco_client)

    def activate(self):
        for(portName,port) in self.parent.ports.items():
            _res = port.activate()
        self.component.activate()
    
    def deactivate(self):
        for(portName,port) in self.parent.ports.items():
            _res = port.deactivate()
        self.component.deactivate()
        
    def terminate(self):
        for(portName,port) in self.parent.ports.items():
            _res = port.terminate()
            
    def runCommand(self,msg):
        stop,err = False,False
        try:
            if msg == Component.STOP:
                self.logger.info("stop")
                self.deactivate()
                self.terminate()
                stop = True
            elif msg == Component.START:
                self.logger.info("start")
                self.updatePoller()
                self.activate()
            elif msg == Component.SETUP:
                self.logger.info("setup")
                self.setup()
            elif msg == Component.FINALIZE:
                self.logger.info("finalize")
                self.finalize()
            else:
                self.logger.warning("unknown command %s" % str(msg))
                err = True           # Should report an error
        except Exception as e:
            traceback.print_exc()
            self.logger.error('runCommand(): %s',str(e))
            err = True
        return (stop,err)
    
    def locateHandler(self,portName):
        handler = self.handlers.get(portName,None)
        if handler:
            return handler
        else:
            funcName = 'on_' + portName
            handler = getattr(self.component, funcName, None)
            if handler is None:
                raise UndefinedHandler(funcName)
            else:
                self.handlers[portName] = handler
        return handler
        
    def executeHandlerFor(self,socket):
        '''
        Execute the handler for the socket
        The handler is always allowed to run to completion, the operation is never preempted. 
        '''
        if socket in self.sock2PortMap:
            portName = self.sock2NameMap[socket]
            portObj = self.sock2PortMap[socket]
            try:
                func_ = self.locateHandler(portName)
                func_()
            except:
                traceback.print_exc()
                raise
        else:
            self.logger.error('Unbound port')
    
    
    def __scheduler(self,sockets):
        for socket in sockets:
            self.executeHandlerFor(socket)

    def scheduler(self, sockets):
        '''
         priority scheduler for the component message processing. 
          
         The priority order is determined by the order of component ports. The dictionary of active sockets is scanned, and the \
         they are inserted into a priority queue (according to their priority value). The queue is processed (in order of \
         priority). After each invocation, the inputs are polled (in a no-wait operation) and the priority queue is updated. 
         '''
        while True:
            for socket in sockets:
                if socket in self.sock2PortMap:
                    pri = self.sock2PrioMap[socket]
                cnt = next(self.tc)
                entry = (pri,cnt,socket)
                heapq.heappush(self.pq,entry)
            sockets = {}
            while True:
                try:
                    pri,cnt,socket = heapq.heappop(self.pq)     # Execute one task
                    self.executeHandlerFor(socket)
                    if len(self.pq) == 0:                       # Empty queue, return
                        return
                    sockets = dict(self.poller.poll(None))      # Poll to check if something came in
                    if sockets:
                        if self.control in sockets:             # Handle control message
                            msg = self.recvControl()
                            self.toStop = self.runCommand(msg)
                            del sockets[self.control]
                            if self.toStop: return              # Return if we must stop
                        if len(sockets):                        # More sockets to handle,
                            break                               #  break from inner loop to schedule tasks
                    else:                                       # Nothing came in
                        continue                                #  keep running inner loop
                except IndexError:                              # Queue empty, return
                    return
 
    def run(self):
        self.setupControl()
        self.setupDisco()
        self.setupPoller()
        self.toStop = False
        while True:
            sockets = dict(self.poller.poll())
            if self.control in sockets:
                msg = self.recvControl()
                (self.toStop,err) = self.runCommand(msg)
                self.sendControl(Component.OK if not err else Component.ERR)
                del sockets[self.control]
            if self.toStop: break
            if len(sockets) > 0: self.scheduler(sockets)
            if self.toStop: break
        # self.logger.info("stopping")
        if hasattr(self.component,'__destroy__'):
            destroy_ = getattr(self.instance,'__destroy__')
            destroy_()
        # self.logger.info("stopped")

class Component(object):
    '''
    classdocs
    '''
    OK = 0 
    ERR = -1
    
    SETUP = 1
    FINALIZE = 2
    START = 3
    STOP  = 4

    def __init__(self):
        class_ = getattr(self,'__class__')
        className = getattr(class_,'__name__')
        self.owner = class_.OWNER                   # This is set in the parent part (temporarily)
        #
        # Logger attributes
        # logger: logger for this class
        # loghandler: handler for the logger (defaults to a StreamHandler)
        # logformatter: formatter assigned to the handler (default: Level:Time:Process:Class:Message)
        
        qualName = self.owner.qualName
        inst_logconf = '%s-log.yaml' % qualName
        comp_logconf = '%s-log.yaml' % className
        done = False
        yaml = YAML()
        try:
            logging.config.dictConfig(yaml.load(pathlib.Path(inst_logconf)))
            done = True
        except Exception:
            try:
                logging.config.dictConfig(yaml.load(pathlib.Path(comp_logconf)))
                done = True 
            except Exception:
                pass
        if not done:
            opt = Config.APP_LOGS
            self.logger = logging.getLogger(qualName)
            self.logger.setLevel(logging.INFO)
            self.logger.propagate=False
            if opt == 'std':
                self.loghandler = logging.StreamHandler()
            elif opt == 'log':
                logFile = "%s.log" % qualName
                self.loghandler = logging.FileHandler(logFile)
            else:
                self.loghandler = logging.NullHandler()
            self.loghandler.setLevel(logging.INFO)
            self.loghandler.addFilter(HostnameFilter())
            self.logformatter = logging.Formatter('%(levelname)s:%(asctime)s:[%(hostname)s.%(process)d]:%(name)s:%(message)s')
            self.loghandler.setFormatter(self.logformatter)
            self.logger.addHandler(self.loghandler)
        #
        self.thread = None
    
    def activate(self):
        pass
    
    def deactivate(self):
        pass
    
    
    
        
