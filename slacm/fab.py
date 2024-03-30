import os
import sys
import shlex
import argparse
import site
import subprocess

def bash(cmd):
    print("=== "+cmd)
    subprocess.run(shlex.split(cmd))

def fab():
    parser = argparse.ArgumentParser()
    # Fabric command
    parser.add_argument("fabcmd", help="fabric command")
    # List of hosts to use (instead of system configured file)
    parser.add_argument("-hosts", default="", help="list of hosts, comma separated")   
    args = parser.parse_args()
    
    fcmd = "fab"
    fflag = "-c"    
    fconfig = "tasks"
    
    rflag = "-r"
    rpath = None
    try:
        import slacm
        rpath = slacm.__path__
        rpath = rpath[0] if type(rpath) == list else str(rpath)
    except:
        print('slacm is missing?')
        os.__exit(1)

    fhosts = ("--hosts=" + args.hosts) if args.hosts else ""
    print(rpath)    
    cmd = str.join(' ',(fcmd,fflag,fconfig,rflag,rpath,args.fabcmd, fhosts))
    try:
        bash(cmd)
    except:
        os._exit(1)        
        
if __name__ == '__main__':
    fab()
    
    