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
    '''
    Parser language exception class
    '''
    def __init__(self, message):
        super(LangError, self).__init__(message)

class App(object):
    '''
    Internal 'App' class representing an application model. Holds the
    relevant content of the model. 
    '''
    def __init__(self,name,messages,libraries,components,actors,deploys):
        self.name = name
        self.messages = messages
        self.libraries = libraries
        self.components = components
        self.actors = actors
        self.deploys = deploys

def parse_model(modelName,verbose=False,debug=False,export=False):
    '''
    Parse model file and construct a model object (using textX).
    :param modelName: name of model file
    :param verbose: verbose operation
    :param debug: debug mode for parser
    :param export: if true meta and model will be experted into a dot file. 
    '''
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


