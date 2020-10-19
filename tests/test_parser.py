'''
Created on Sep 19, 2020

@author: esdev
'''
import argparse
from slacm.parser import parse_model

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("model", help="model file")
    parser.add_argument("-v","--verbose", help="verbose message", action="store_true")
    parser.add_argument("-d","--debug", help="debug parser", action="store_true")
    parser.add_argument("-x","--export", help="export meta and model", action="store_true")
    args = parser.parse_args()
    parse_model(args.model,args.verbose,args.debug,args.export)
    
    