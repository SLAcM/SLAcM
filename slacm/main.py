'''
Created on Sep 18, 2020

@author: esdev
'''

import sys
import os,signal
import argparse
import traceback
import logging

from slacm.app import App
from slacm.config import Config

theConfig = None
theApp = None

def terminate(signal,frame):
    global theDepl
    theApp.terminate()
    
def slacm():
    parser = argparse.ArgumentParser()
    parser.add_argument("model", help="model/package file")
    parser.add_argument("-v","--verbose", help="verbose messages", action="store_true")
    parser.add_argument("-r","--root", help="root host:disco_port:pub_port:sub_port")

    try:
        args = parser.parse_args()
    except: 
        print ("slacm_run: unexpected error:", sys.exc_info()[0])
        raise

    if not os.path.exists(args.model):
        print(os.getcwd())
        print("slacm_run: model/package '%s' does not exist" % args.model)
        raise 
    
    signal.signal(signal.SIGTERM,terminate)
    signal.signal(signal.SIGINT,terminate)
    
    try:
        global theApp
        theApp = App(args.model,args.verbose,args.root)
        theApp.setup()
        theApp.run()
        theApp.join()
    except:
        if args.verbose:
            traceback.print_exc()
        print ("slacm_run: Fatal error: %s" % (sys.exc_info()[1],))
        os._exit(1)
        
if __name__ == '__main__':
    pass

