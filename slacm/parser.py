'''
Created on Sep 18, 2020

@author: esdev
'''

from os.path import join
from textx.metamodel import metamodel_from_file
from textx.export import metamodel_export, model_export
from textx.exceptions import TextXSemanticError, TextXSyntaxError
import textx.model

import sys
import json
import os
import argparse

class LangError(Exception):
    def __init__(self, message):
        super(LangError, self).__init__(message)

class App(object):
    def __init__(self,name,messages,libraries,components,actors,deploys):
        self.name = name
        self.messages = messages
        self.libraries = libraries
        self.components = components
        self.actors = actors
        self.deploys = deploys

def parse_model(modelName,verbose=False,debug=False,export=False):
    dir_path = os.path.dirname(os.path.abspath(__file__))
    this_folder = os.getcwd() 
    meta = metamodel_from_file(join(dir_path,'slacm.tx'),
                               classes=[App],
                               debug=debug)
    if export: 
        metamodel_export(meta, join(this_folder, 'slacm_meta.dot'))
    try:
        model = meta.model_from_file(join(os.getcwd(),modelName))
    except IOError as e:
        errMsg = "I/O error({0}): {1}".format(e.errno, e.strerror)
        if verbose: print (errMsg)
        raise LangError(errMsg)
    except TextXSyntaxError as e:
        errMsg = "Syntax error: %s" % e.args
        if verbose: print (errMsg)
        raise LangError(errMsg)
    except TextXSemanticError as e:
        errMsg = "Semantic error: %s" % e.args
        if verbose: print (errMsg)
        raise LangError(errMsg)
    except Exception as e: 
        errMsg = "Unexpected error %s:%s" % (sys.exc_info()[0],e.args())
        if verbose: print (errMsg)
        raise LangError(errMsg)
    if export:
        model_export(model, join(this_folder, 'slacm_model.dot'))
    return model


if __name__ == '__main__':
    pass


