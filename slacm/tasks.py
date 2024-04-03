'''
Created on Oct 17, 2020

@fabric.author: esdev
'''
import os
import fabric
from fabric import task
# from fabric import api, operations
# from fabric.api import env,hosts,local,run,serial,settings, task
#from fabric.context_managers import hide

""" class env():
    # Standard fabric configuration
    shell = "/bin/bash -l -i -c"
    parallel = True            # Changes default behavior to parallel
    use_ssh_config = False     # Tells fabric to use the user's ssh config
    disable_known_hosts = True # Ignore warnings about known_hosts
    user = 'slacm'
    # File transfer directories
    localPath = os.getcwd() + '/' # Path on localhost
    nodePath = '/home/slacm/'  # Path on target
    hosts = ['rpi4car']
    version = '0.0.2' """

@task
def run(ctx,cmd):
    """Execute command as user:<command>"""
    # ctx.user = env.user
    # print("["+ctx.host+"] " + cmd)
    result = ctx.run(cmd,shell=env.shell,hide=True,warn=True)
    print(result)
    return result

@task
def sudo(ctx,cmd):
    """Execute command as sudo:<command>"""
    ctx.user = env.user
    print("["+ctx.host+"] " + cmd)
    result = ctx.sudo(cmd,shell=env.shell,hide=True,warn=True)
    print(result)
    return result


@task
def check(c):
    """Test that hosts are communicating"""
    run(c,'hostname && uname -a')

@task
def build(c):
    """Build package locally"""
    c.run("python setup.py sdist bdist_wheel")
 
@task
def install(c):
    """ Install package locally - must be run w/ sudo"""
    c.sudo("python setup.py install")
    c.sudo("rm -fr dist/ build/ slacm.egg-info/")
    
@task
def uninstall(c):
    """ Uninstall package locally - must be run w/ sudo"""
    package = 'slacm'
    c.sudo('pip uninstall -y %s' % package)
    
@task
def get(ctx,fileName, local_path='.'):
    """Download file from host:<file name>,[local path]"""
    ctx.local("scp %s@%s:%s %s" % (env.user,ctx.host,fileName,local_path))
 
@task
def put(ctx,fileName, remote_path=''):
    """Upload file to hosts:<file name>,[remote path]"""
    ctx.local("scp %s %s@%s:%s" % (fileName,env.user,ctx.host,remote_path))
     
@task
def deploy(c):
    """Deploy package on remote host(s)"""
    c.local("python setup.py sdist")
    package = 'slacm-' + str(env.version) + '.tar.gz'
    package_path = 'dist/' + package
    put(c,package_path)
    sudo(c,'pip install %s' % package)
    sudo(c,'rm -f %s' %(package))
     
@task
def undeploy(c):
    """Uninstall package on remote hosts(s)"""
    package = 'slacm'
    sudo(c,'pip uninstall -y %s' % package)

@task
def wipe(c):
    """Wipe all user files on remote host(s)"""
    sudo(c,'rm -fr /home/%s/[a-zA-Z]*' % env.user)
    
@task
def requires(c):
    """Install requirements om remote host(s)"""
    put(c,"requirements.txt")
    sudo(c,"pip install -r requirements.txt")
    run(c,'rm -f requirements.txt')
     
@task
def kill(c):
    """Kill any hanging processes"""
    sudo(c,"pkill -SIGKILL slacm_run")
     
@task
def stop(c):
    """Stop local slacm process"""
    c.run("pkill -SIGTERM -f slacm_run")
    
@task
def shutdown(c):
    """Shutdown all hosts"""
    sudo(c,"shutdown now")
        
     