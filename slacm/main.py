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

if sys.platform == "linux":
    import termios
    theTermFD = None
    theTermAttr = None

    def saveTerm():
        if platform == "linux":
            global theTermFD,theTermAttr
            try:
                theTermFD = sys.stdin.fileno()
                theTermAttr = termios.tcgetattr(theTermFD)
            except:
                pass

    def restoreTerm():
        global theTermFD,theTermAttr
        if theTermFD:
            termios.tcsetattr(theTermFD,termios.TCSADRAIN,theTermAttr)
        else:
            pass


else:
    def saveTerm(): pass

    def restoreTerm(): pass

def terminate(_signal,_frame):
    global theApp
    restoreTerm()
    theApp.terminate()
        
def slacm():
    '''
    Main entry point to SLAcM - called from the command line.
    Arguments: model [-v|--verbose] [-r:--root host:disco_port:pub_port:sub_port]
    The last argument is used only on remote, peer nodes. 
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("model", help="model/package file")
    parser.add_argument("-v","--verbose", help="verbose messages", action="store_true")
    parser.add_argument("-r","--root", help="root host:disco_port:pub_port:sub_port")

    try:
        args = parser.parse_args()
    except: 
        print ("slacm_run: model parsing failed")
        sys.exit()

    if not os.path.exists(args.model):
        print(os.getcwd())
        print("slacm_run: model/package '%s' does not exist" % args.model)
        sys.exit() 
    
    saveTerm()
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
        restoreTerm()
        sys.exit()
        
if __name__ == '__main__':
    slacm()

