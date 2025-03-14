'''
Created on Sep 18, 2020

@author: esdev
'''

import collections
import fabric
import os
import getpass
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
from slacm.exceptions import PortOperationError,PeerOperationError,BuildError,ArgumentError
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
    Class representing an application. Instantiated by the main(), as a singleton.
    Constructs and runs the application on the current ('root') and on remote ('peer') nodes. 
    '''
    MODE_SIMPLE = 1
    MODE_ROOT   = 2
    MODE_PEER  = 3
    
    def __init__(self,arg,verbose,arg2):
        '''
        Constructor for the App class.
        :param arg: name of model (.slacm) file.
        :param verbose: verbose flag
        :param arg2: root specification string for peer nodes, or None (for root node)
        '''
        self.verbose = verbose
        self.mode = None
        if arg2:
            try:
                parsed = parse.parse("{host}:{disco_port:d}:{pub_port:d}:{sub_port:d}",arg2)
                self.root_host = parsed['host']
                self.root_port = parsed['disco_port']
                self.root_pub_port = parsed['pub_port']
                self.root_sub_port = parsed['sub_port']
                self.mode = App.MODE_PEER
            except:
                raise ArgumentError(f"invalid --root argument for peer: {arg2}")
        
        self.app = None
        if self.mode == App.MODE_PEER:
            try:
                with tarfile.open(arg,"r:gz") as tar:
                    tar.extractall('./')
            except Exception as ex:
                emsg = f"Extracting app package: {type(ex)}({ex.args}) failed"
                print(f"slacm_run:{emsg}")
                raise BuildError(emsg)
            
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
                host_aliases = { self.hostname, f"{self.hostname}.local", f"{self.hostname}.lan",\
                                self.netInfo.globalHost, self.netInfo.localHost }
                self.params_host = 'host'
                for host in host_aliases:
                    if self.params.is_host(host):
                        self.params_host = host
                        break 
                for host in self.peer_deplo:
                    if host in host_aliases:
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
                            with fabric.connection.Connection(host,user=Config.TARGET_USER,
                                                              connect_kwargs = { 
                                                                                "key_filename": f"/home/{getpass.getuser()}/.ssh/id_rsa"
                                                                                }) as conn:
                                
                                xfer = fabric.transfer.Transfer(conn)
                                xfer.put(pack,dist)
                            self.peer_hosts += [host]
                        except Exception as e:
                            emsg = f"Couldn't deploy app package on {host}: {e}"
                            self.logger.error(emsg)
                            raise BuildError(emsg) from e
                    self.make_peer_arg()
                    try:
                        self.peer_group = fabric.ThreadingGroup(*self.peer_hosts,user=Config.TARGET_USER,
                                                                 connect_kwargs = { 
                                                                                "key_filename": f"/home/{getpass.getuser()}/.ssh/id_rsa"
                                                                                })
                    except Exception as e:
                        emsg = f"Couldn't form peer group: '{e}'"
                        self.logger.error(emsg)
                        raise BuildError(emsg) from e
                    self.peer_runner = threading.Thread(target=self.run_peers, args=(dist,))
                    self.peer_runner.start()
                    time.sleep(1.0)
                    if not self.peer_runner.is_alive():
                        raise PeerOperationError("Error launching peers")
                for depl in self.root_deplo:
                    actorModel = depl.actor
                    self.actors[actorModel.name]=Actor(self,actorModel)
        
    def get_actor_params(self,actor):
        '''
        Return the parameters specific to an actor of the application. 
        '''
        return self.params.get_actor_params(self.params_host,actor)
    
    def get_comp_params(self,actor,component):
        '''
        Return the parameters specific to a component of an actor of the application. 
        '''
        return self.params.get_comp_params(self.params_host,actor,component) 
        
    def run_peers(self,dist):
        '''
        Launch SLAcM on the peer node/s, with the distribution parameter 
        '''
        try:
            cmd = "slacm_run %s -r %s %s" % ("-v" if self.verbose else "", self.peer_arg,dist)
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
        '''
        Set up ports for the root App used to communicate with peer nodes. 
        '''
        self.root_pub = self.context.socket(zmq.PUB)
        self.root_pub_port = self.root_pub.bind_to_random_port("tcp://" + self.netInfo.globalHost)
        self.root_sub = self.context.socket(zmq.SUB)
        self.root_sub.setsockopt_string(zmq.SUBSCRIBE, '')
        self.root_sub_port = self.root_sub.bind_to_random_port("tcp://" + self.netInfo.globalHost)
        
    def make_peer_arg(self):
        '''
        Form the command line argument for the peer nodes.
        '''
        self.disco_host,self.disco_port = self.disco.root()
        self.peer_arg = "%s:%r:%r:%r" % (self.disco_host,self.disco_port,self.root_pub_port,self.root_sub_port)
    
    def setup_peer_ports(self):
        '''
        Set up ports for the peer App used to communicate with the root node.
        '''
        self.peer_pub = self.context.socket(zmq.PUB)
        self.peer_pub.connect("tcp://%s:%d" % (self.root_host, self.root_sub_port))
        self.peer_sub = self.context.socket(zmq.SUB)
        self.peer_sub.setsockopt_string(zmq.SUBSCRIBE, '')
        self.peer_sub_port = self.peer_sub.connect("tcp://%s:%d" % (self.root_host, self.root_pub_port))
            
    def parse_deplo(self):
        '''
        Parse the deployment section of the model. 
        '''
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
        '''
        Determine the network interface used to communicate within the SLAcM network.
        Note: the root and peer nodes may use different network interfaces. 
        Builds the network information record.
        '''
        (globalIPs,globalMACs,_globalNames,localIP,found) = get_network_interfaces()
        try:
            assert len(globalIPs) > 0 and len(globalMACs) > 0
        except:
            self.logger.error("No active network interface")
            raise BuildError("no active network interface")
        if not found:
            self.logger.error("Configured interface: '%s' not found" % Config.NIC_NAME)
            self.logger.info("Using interface for '%s'" % str(globalIPs[0]))
        globalIP = globalIPs[0]
        globalMAC = globalMACs[0]
        self.netInfo = NetInfo(globalHost=globalIP, localHost=localIP, macAddress=globalMAC)
    
    def get_disco(self):
        '''
        Return the discovery manager.
        '''
        return self.disco
    
    def get_netInfo(self):
        '''
        Return the network information record.
        '''
        return self.netInfo
    
    def _slacm_uid_gid(self,tarinfo):
        tarinfo.uname = tarinfo.gname = Config.TARGET_USER
        return tarinfo 
    
    def build_package(self):
        '''
        Build a deployment package from the content of the application folder, where the model file is contained.
        :return tgz_file: the full path of the package file.  
        '''
        modelFilePath = pathlib.Path(self.modelFile).resolve()
        modelFileParent = modelFilePath.parent
        currentDir = os.getcwd()
        os.chdir(modelFileParent.parent)
        packName = modelFileParent.name
        tempDir = tempfile.mkdtemp()                        # Temp folder
        tgz_file = os.path.join(tempDir,packName + '.tgz')  # Construct tgz file
        with tarfile.open(tgz_file,"w:gz") as tar:
            tar.add(packName,filter=self._slacm_uid_gid)
        os.chdir(currentDir)
        return tgz_file
    
    def broadcast_to_peers(self,msg):
        '''
        Broadcast a message from the root to all peers.
        :param msg: Message to broadcast
        '''
        if self.mode == App.MODE_SIMPLE: return
        assert self.mode == App.MODE_ROOT
        try:
            self.root_pub.send_pyobj(msg)
        except zmq.error.ZMQError as e:
            raise PortOperationError(f"broadcast to peers [{e.errno}]") from e
        
    def collect_from_peers(self,arg=None):
        '''
        Collect an expected message from all peer nodes on the root node.
        :param arg: Expected message string 
        '''
        if self.mode == App.MODE_SIMPLE: return None
        assert self.mode == App.MODE_ROOT
        res = { }
        for _h in range(len(self.peer_hosts)):
            try:
                msg = self.root_sub.recv_pyobj()
                if arg:
                    assert arg == msg
            except zmq.error.ZMQError as e:
                raise PortOperationError(f"collect from peers [{e.errno}]") from e
            res[_h] = msg
        return res

    def recv_from_root(self,arg=None):
        '''
        Expect and receivee message from the root on a peer node.
        :param arg: Message expected
        '''
        if self.mode == App.MODE_SIMPLE: return None
        assert self.mode == App.MODE_PEER
        try:
            msg = self.peer_sub.recv_pyobj()
            if arg:
                assert arg == msg
        except zmq.error.ZMQError as e:
            raise PortOperationError(f"recv from root [{e.errno}]") from e
        return msg
    
    def send_to_root(self,msg):
        '''
        Send a message to the root from a peer node.
        :param msg: Message to send.
        '''
        if self.mode == App.MODE_SIMPLE: return
        assert self.mode == App.MODE_PEER
        try:
            self.peer_pub.send_pyobj(msg)
        except zmq.error.ZMQError as e:
            raise PortOperationError(f"send to root [{e.errno}]") from e
                   
    def setup(self):
        '''
        Execute the 'setup' and 'finalize' steps in application initialization.
        The same code runs on the root and the peer nodes, but execution is 
        synchronized through messages. The expected sequence: (1) peers ready,
        (2) setup executed, (3) finalize executed. 
        '''
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
        '''
        Run the actors of the node (root or peer)
        '''
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
        '''
        On a root node: execute a 'join' for all actors.
        On a peer node: wait for a 'terminate' message from the root, and then terminate
        '''
        if self.mode == App.MODE_PEER:
            _msg = self.recv_from_root('root.terminate')
            self.terminate()
        else:
            for (_name,actor) in self.actors.items():
                actor.join()
        if self.mode == App.MODE_ROOT and self.peer_runner:
            self.peer_runner.join()

    def terminate(self):
        '''
        Terminate actvities of the current app. 
        '''
        self.logger.info("terminate")
        if self.mode == App.MODE_ROOT:
            self.broadcast_to_peers('root.terminate')
        for (_name,actor) in self.actors.items():
            actor.terminate()
        self.disco.stop()
        os._exit(0)
        
        
        
        
            
            