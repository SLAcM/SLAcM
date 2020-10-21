'''
Created on Sep 18, 2020

@author: esdev
'''

import collections
import fabric
import os
import parse
import pathlib
import platform
import zmq
import tarfile
import tempfile
import threading
import time
import sys
import logging

from slacm.actor import Actor
from slacm.config import Config
from slacm.parser import parse_model
from slacm.exceptions import PortOperationError,PeerOperationError
from slacm.utils import get_network_interfaces
from slacm.discovery import DiscoveryService
from slacm.params import Params
from slacm.utils import NetInfo

try:
    import cPickle
    pickle = cPickle
except:
    cPickle = None
    import pickle
    

DeplInfo = collections.namedtuple('DeplInfo', 'actor params')

class App(object):
    '''
    classdocs
    '''
    MODE_SIMPLE = 1
    MODE_ROOT   = 2
    MODE_PEER  = 3
    
    def __init__(self,arg,verbose,arg2):
        '''
        Constructor
        '''
        self.verbose = verbose
        self.mode = None
        if arg2:
            parsed = parse.parse("{host}:{disco_port:d}:{pub_port:d}:{sub_port:d}",arg2)
            self.root_host = parsed['host']
            self.root_port = parsed['disco_port']
            self.root_pub_port = parsed['pub_port']
            self.root_sub_port = parsed['sub_port']
            self.mode = App.MODE_PEER
        
        self.app = None
        if self.mode == App.MODE_PEER:
            try:
                with tarfile.open(arg,"r:gz") as tar:
                    tar.extractall('./')
            except Exception as ex:
                print("slacm_run: Extract app package: %s(%s)" % (str(type(ex)),str(ex.args)))
                raise 
            
            app = pathlib.Path(arg).resolve().stem
            model = pathlib.Path(app,str(app) + '.slacm')
            if model.exists:
                self.modelFile = str(model)
            else:
                files = [f for f in pathlib.Path(app).glob('*.slacm')]
                self.modelFile = str(files[0])
        else:
            self.modelFile = arg
        
        
        if not os.path.exists(self.modelFile):
            print("slacm_run: model/package '%s' does not exist" % self.modelFile)
        
        modelFilePath = os.path.abspath(self.modelFile)
        modelFileDir = os.path.dirname(modelFilePath)
        os.chdir(modelFileDir)
        self.modelFile = str(modelFilePath)
        self.app = pathlib.Path(modelFilePath).stem 
    
        sys.path.append(os.getcwd())   # Ensure load_module works from current directory
    
        try:
            global theConfig
            theConfig = Config('SLACM')
        except:
            print("slacm_run: Error reading configuration:", sys.exc_info()[0])
            pass
    
        self.logger = logging.getLogger(__name__)
        
        self.messages = {}
        self.components = {}      
        self.actors = {}
        self.deploys = {}
        
        self.model = parse_model(self.modelFile,verbose)
        
        self.setupInterfaces()
        self.hostname = platform.node()
        
        self.params = Params(self.app + '.params')
        self.params_host = None 
                
        self.context = zmq.Context()
                
        if self.mode == App.MODE_PEER:
            self.disco = DiscoveryService(self.context,self.root_host,self.root_port)
        else:
            self.disco = DiscoveryService(self.context,self.netInfo.globalHost)
  
        self.peer_hosts = [] 
        if not self.model.deploys:
            self.mode = App.MODE_SIMPLE
            self.params_host = 'root'
            for actorModel in self.model.actors:
                self.actors[actorModel.name] = Actor(self,actorModel)
        else:
            self.parse_deplo()
            if self.mode == App.MODE_PEER:
                self.setup_peer_ports()
                this_host = { self.hostname, self.netInfo.globalHost, self.netInfo.localHost }
                for host in this_host:
                    if self.params.is_host(host):
                        self.params_host = host
                        break 
                self.param_host = self.hostname
                for host in self.peer_deplo:
                    if host in this_host:
                        for depl in self.peer_deplo[host]:
                            actorModel = depl.actor
                            self.actors[actorModel.name]=Actor(self,actorModel)       
            else:
                self.mode = App.MODE_ROOT
                self.params_host = 'root'
                self.setup_root_ports()
                self.peer_runner = None
                if len(self.peer_deplo) > 0: 
                    pack = self.build_package()
                    dist = pathlib.Path(pack).name
                    for host in self.peer_deplo:
                        try:
                            with fabric.connection.Connection(host,user=Config.TARGET_USER) as conn:
                                xfer = fabric.transfer.Transfer(conn)
                                xfer.put(pack,dist)
                            self.peer_hosts += [host]
                        except Exception as e:
                            self.logger.error("Couldn't deploy app package: '%s'", str(e))
                            raise
                    self.make_peer_arg()
                    try:
                        self.peer_group = fabric.ThreadingGroup(*self.peer_hosts,user=Config.TARGET_USER)
                    except Exception as e:
                        self.logger.error("Couldn't form peer group: '%s'", str(e))
                        raise
                    self.peer_runner = threading.Thread(target=self.run_peers, args=(dist,))
                    self.peer_runner.start()
                    time.sleep(1.0)
                    if not self.peer_runner.is_alive():
                        raise PeerOperationError("Error launching peers")
                for depl in self.root_deplo:
                    actorModel = depl.actor
                    self.actors[actorModel.name]=Actor(self,actorModel)
    
    def get_actor_params(self,actor):
        return self.params.get_actor_params(self.params_host,actor)
    
    def get_comp_params(self,actor,component):
        return self.params.get_comp_params(self.params_host,actor,component) 
        
    def run_peers(self,dist):
        try:
            cmd = "slacm_run -r %s %s" % (self.peer_arg,dist)
            if Config.SUDO:
                res = self.peer_group.run("sudo " + cmd)
            else:
                res = self.peer_group.run(cmd)
        except fabric.exceptions.GroupException as exc:
            self.logger.error("Couldn't start peers: '%s'", cmd)
            print(exc) 
            res = exc
        return res
            
    def setup_root_ports(self):
        self.root_pub = self.context.socket(zmq.PUB)
        self.root_pub_port = self.root_pub.bind_to_random_port("tcp://" + self.netInfo.globalHost)
        self.root_sub = self.context.socket(zmq.SUB)
        self.root_sub.setsockopt_string(zmq.SUBSCRIBE, '')
        self.root_sub_port = self.root_sub.bind_to_random_port("tcp://" + self.netInfo.globalHost)
        
    def make_peer_arg(self):
        self.disco_host,self.disco_port = self.disco.root()
        self.peer_arg = "%s:%r:%r:%r" % (self.disco_host,self.disco_port,self.root_pub_port,self.root_sub_port)
    
    def setup_peer_ports(self):
        self.peer_pub = self.context.socket(zmq.PUB)
        self.peer_pub.connect("tcp://%s:%d" % (self.root_host, self.root_sub_port))
        self.peer_sub = self.context.socket(zmq.SUB)
        self.peer_sub.setsockopt_string(zmq.SUBSCRIBE, '')
        self.peer_sub_port = self.peer_sub.connect("tcp://%s:%d" % (self.root_host, self.root_pub_port))
            
    def parse_deplo(self):
        on_root,on_all,on_hosts = [],[],{ }
        all_hosts = set()
        for deploy in self.model.deploys:
            location = deploy.location
            if location.root == 'root':
                on_root += [deploy.performers]
            elif location.all == 'all':
                on_all += [deploy.performers]
            else:
                for host in location.hosts:
                    all_hosts.add(host)
                    if host in on_hosts:
                        on_hosts[host] += [deploy.performers]
                    else:
                        on_hosts[host] = deploy.performers

        root_deplo = set()
        for pl in on_root:
            for p in pl:
                root_deplo.add(DeplInfo(actor=p.actor,params=p.params))
        for pl in on_all:
            for p in pl:
                root_deplo.add(DeplInfo(actor=p.actor,params=p.params))
        self.root_deplo = root_deplo

        peer_deplo = { }
        for host,perfs in on_hosts.items():
            peer_perfs = set()
            for p in perfs:
                peer_perfs.add(DeplInfo(actor=p.actor,params=p.params))
            peer_deplo[host.name] = peer_perfs
        for pl in on_all:
            for host in all_hosts:
                for p in pl:
                    peer_deplo[host.name].add(DeplInfo(actor=p.actor,params=p.params))
        self.peer_deplo = peer_deplo

    def setupInterfaces(self):
        (globalIPs,globalMACs,_globalNames,localIP,found) = get_network_interfaces()
        try:
            assert len(globalIPs) > 0 and len(globalMACs) > 0
        except:
            self.logger.error("Error: no active network interface")
            raise
        if not found:
            self.logger.error("Configured interface: '%s' not found" % Config.NIC_NAME)
            self.logger.info("Using interface for '%s'" % str(globalIPs[0]))
        globalIP = globalIPs[0]
        globalMAC = globalMACs[0]
        self.netInfo = NetInfo(globalHost=globalIP, localHost=localIP, macAddress=globalMAC)
    
    def get_disco(self):
        return self.disco
    
    def get_netInfo(self):
        return self.netInfo
    
    def build_package(self):
        modelFilePath = pathlib.Path(self.modelFile).resolve()
        modelFileParent = modelFilePath.parent
        currentDir = os.getcwd()
        os.chdir(modelFileParent.parent)
        packName = modelFileParent.name
        tempDir = tempfile.mkdtemp()                        # Temp folder
        tgz_file = os.path.join(tempDir,packName + '.tgz')  # Construct tgz file
        with tarfile.open(tgz_file,"w:gz") as tar:
            tar.add(packName)
        os.chdir(currentDir)
        return tgz_file
    
    def broadcast_to_peers(self,msg):
        if self.mode == App.MODE_SIMPLE: return
        assert self.mode == App.MODE_ROOT
        try:
            self.root_pub.send_pyobj(msg)
        except zmq.error.ZMQError as e:
            raise PortOperationError("broadcast to peers (%d)" % e.errno) from e
        
    def collect_from_peers(self,arg=None):
        if self.mode == App.MODE_SIMPLE: return None
        assert self.mode == App.MODE_ROOT
        res = { }
        for _h in range(len(self.peer_hosts)):
            try:
                msg = self.root_sub.recv_pyobj()
                if arg:
                    assert arg == msg
            except zmq.error.ZMQError as e:
                raise PortOperationError("collect from peers (%d)" % e.errno) from e
            res[_h] = msg
        return res

    def recv_from_root(self,arg=None):
        if self.mode == App.MODE_SIMPLE: return None
        assert self.mode == App.MODE_PEER
        try:
            msg = self.peer_sub.recv_pyobj()
            if arg:
                assert arg == msg
        except zmq.error.ZMQError as e:
            raise PortOperationError("recv from root (%d)" % e.errno) from e
        return msg
    
    def send_to_root(self,msg):
        if self.mode == App.MODE_SIMPLE: return
        assert self.mode == App.MODE_PEER
        try:
            self.peer_pub.send_pyobj(msg)
        except zmq.error.ZMQError as e:
            raise PortOperationError("send to root (%d)" % e.errno) from e
                   
    def setup(self):
        self.logger.info("App.setup: mode = %d" % self.mode)
        if  self.mode == App.MODE_ROOT:
            self.collect_from_peers('peer.ready')
        elif self.mode == App.MODE_PEER:
            time.sleep(1.0)
            self.send_to_root('peer.ready')
        else:
            pass
        
        if self.mode == App.MODE_ROOT:
            self.broadcast_to_peers('setup.start')
        elif self.mode == App.MODE_PEER:
            _msg = self.recv_from_root('setup.start')
        else:
            pass
        
        for (_name,actor) in self.actors.items():
            actor.setup()
        self.logger.info('setup done')
       
        if self.mode == App.MODE_ROOT:
            self.collect_from_peers('setup.done')
        elif self.mode == App.MODE_PEER:
            self.send_to_root('setup.done')
        else:
            pass
        
        if self.mode == App.MODE_ROOT:
            self.broadcast_to_peers('finalize.start')
        elif self.mode == App.MODE_PEER:
            _msg = self.recv_from_root('finalize.start')
        else:
            pass

        for (_name,actor) in self.actors.items():
            actor.finalize()
            
        if self.mode == App.MODE_ROOT:
            self.collect_from_peers('peer.ready')
        elif self.mode == App.MODE_PEER:
            self.send_to_root('peer.ready')
        else:
            pass
        
        self.logger.info('finalize done')
        
    def run(self):
        if self.mode == App.MODE_ROOT:
            self.broadcast_to_peers('root.run')
        elif self.mode == App.MODE_PEER:
            _msg = self.recv_from_root('root.run')
        else:
            pass
        
        for (_name,actor) in self.actors.items():
            actor.run()
            
        self.logger.info("run done")

    def join(self):
        if self.mode == App.MODE_PEER:
            _msg = self.recv_from_root('root.terminate')
            self.terminate()
        else:
            for (_name,actor) in self.actors.items():
                actor.join()
        if self.mode == App.MODE_ROOT and self.peer_runner:
            self.peer_runner.join()

    def terminate(self):
        self.logger.info("terminate")
        if self.mode == App.MODE_ROOT:
            self.broadcast_to_peers('root.terminate')
        for (_name,actor) in self.actors.items():
            actor.terminate()
        self.disco.stop()
        os._exit(0)
        
        
        
        
            
            