'''
Created on Sep 19, 2020

@author: esdev
'''

'''
Created on Nov 23, 2016

@author: slacm
'''

import configparser
import os
from os import path
from os.path import join
import platform
import logging
import logging.config
import pathlib
from ruamel.yaml import YAML

class HostnameFilter(logging.Filter):
    hostname = platform.node()

    def filter(self, record):
        record.hostname = HostnameFilter.hostname
        return True

# handler = logging.StreamHandler()
# handler.addFilter(HostnameFilter())
# handler.setFormatter(logging.Formatter('%(asctime)s %(hostname)s: %(message)s', datefmt='%b %d %H:%M:%S'))


class Config(object):
    '''
    Configuration database for SLAM
    Including logging configuration
    '''
    TARGET_USER = 'slacm'
    SEND_TIMEOUT = -1
    RECV_TIMEOUT = -1
    NIC_NAME = None
    TRACE = ''
    SUDO = True
    APP_LOGS = 'std'
    
    def __init__(self,base):
        '''
        Construct the configuration object that configures the logger and various system parameters. 
        The logger and system configuration are set according to the content of the files slacm-log.conf
        and slacm.conf 
        '''
        slacm_folder = os.getcwd()
#         slacm_logconf = join(slacm_folder,'slacm-log.conf')
#         
#         if path.exists(slacm_logconf):
#             try:
#                 logging.config.fileConfig(slacm_logconf)
#             except Exception as e:
#                 logging.warning('Log config file [%s] error: %s.' % (slacm_logconf, str(e)))
#                 pass
#   
        slacm_logconf = join(slacm_folder,'slacm-log.yaml')
        
        if not path.exists(slacm_logconf):
            logging.info("No log config file: %s" % slacm_logconf)  
        else:
            self.yaml = YAML()

            try:
                logging.config.dictConfig(self.yaml.load(pathlib.Path(slacm_logconf)))
            except Exception as e:
                logging.warning('Log config file [%s] error: %s.' % (slacm_logconf, str(e)))
        
        logger = logging.getLogger(__name__)
        
        slacm_conf_file = join(slacm_folder,'slacm.conf')
        c_parse = configparser.ConfigParser()
    
        if not path.exists(slacm_conf_file):
            logger.warning("No config file: %s" % slacm_conf_file)  
            return
            
        files = []      
        try:
            files = c_parse.read(slacm_conf_file)
        except Exception as e:
            pass
        
        if len(files) == 0:
            logger.warning('Config file [%s] has error(s): %s.' % (slacm_conf_file, str(e)))
            return 
        
        host = platform.node()
        sections = ["%s.%s" % (base,host), "%s" % base ]
        
        for slacm_section in sections: 
            if not c_parse.has_section(slacm_section):
                logger.info('Config file [%s] has no section %s.' % (slacm_conf_file, slacm_section))
                continue
            else:
                logger.info('Reading section %s' % (slacm_section))
                try: 
                    for item in c_parse.items(slacm_section):
                        key,arg = item
                        opt = key.upper()
                    
                        if hasattr(Config,opt):
                            optType = type(getattr(Config,opt))
                            optValue = getattr(Config,opt)
                            try:
                                if optType == str:
                                    optValue = str(arg)
                                elif optType == int:
                                    optValue = int(arg)
                                elif optType == bool:
                                    try:
                                        optValue = c_parse.getboolean(slacm_section,key)
                                    except:
                                        pass
                                elif optType == float:
                                    optValue = float(arg)
                                else:
                                    optValue = arg
                                setattr(Config,opt,optValue)
                            except:
                                logger.warning('Formal and actual type of configuration argument %s differ %s - ignored'
                                               % (str(opt), str(optType)))
                                pass
                except:
                    logger.warning('Error reading configuration file %s.' % (slacm_conf))
                    continue
                logger.info('Configuration read')
                break
            
            
            

