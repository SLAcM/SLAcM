'''
Created on Oct 10, 2020

@author: esdev
'''

import pathlib
from ruamel.yaml import YAML

from slacm.exceptions import ParameterLoadError

class Params(object):
    '''
    Parameters are stored as YAML files, of the following format:
    hostname_or_host:
       actor_name:
          component_name:
            param_name: param_value
    '''
    def __init__(self, param_file=None):
        '''
        Constructor for the parameter object.
        Loads the parameter (YAML) file. 
        '''
        self.param_file = param_file
        if param_file == None: return
        self.yaml = YAML()
        self.params = None
        try:
            self.params = self.yaml.load(pathlib.Path(self.param_file)) 
        except FileNotFoundError:
            pass
        except Exception as e:
            raise ParameterLoadError("parameter loading of '%s' failed: %s" % (self.param_file, str(e)))
    
    def is_host(self,host):
        return host in self.params if self.params else None
    
    def get_host_params(self,host):
        return (self.params.get(host,None) or \
                self.params.get('host',None)) if self.params else None
    
    def get_actor_params(self,host,actor):
        host_params = self.get_host_params(host)
        return host_params.get(actor,None) if host_params else None
    
    def get_comp_params(self,host,actor,component):
        actor_params = self.get_actor_params(host, actor)
        return actor_params.get(component,None) if actor_params else None
    
