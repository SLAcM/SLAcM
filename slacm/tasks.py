'''
Created on Oct 17, 2020

@fabric.author: esdev
'''
import os
import fabric
from fabric import task

@task
def run(ctx,cmd):
    """Execute command as user:<command>"""
    # print(f"[{ctx.host}] {cmd}")
    result = ctx.run(cmd) # ,shell=env.shell,hide=True,warn=True)
    # print(f"{result}")
    return result

@task
def sudo(ctx,cmd):
    """Execute command as sudo:<command>"""
    # print(f"[{ctx.host} sudo] {cmd}")
    result = ctx.sudo(cmd) # ,shell=env.shell,hide=True,warn=True)
    # print(f"{result}")
    return result


@task
def check(c):
    """Test that hosts are communicating"""
    run(c,'hostname && uname -a')

@task
def install(c):
    """[sudo] Install package locally from current directory"""
    c.sudo("pip install . --break-system-packages")
    c.sudo("rm -fr dist/ build/ slacm.egg-info/")
    
@task
def uninstall(c):
    """ Uninstall package locally [sudo] """
    package = 'slacm'
    c.sudo('pip uninstall -y %s --break-system-packages' % package)
    
@task
def get(ctx,fileName, local_path='.'):
    """Download file from host:<file name>,[local path]"""
    ctx.local("scp %s@%s:%s %s" % (ctx.config.user,ctx.host,fileName,local_path))
 
@task
def put(ctx,fileName, remote_path='.'):
    """Upload file to hosts:<file name>,[remote path]"""
    ctx.local("scp %s %s@%s:%s" % (fileName,ctx.config.user,ctx.host,remote_path))
     
@task
def deploy(c):
    """Deploy package on remote host(s)"""
    c.local("python setup.py sdist")
    package = 'slacm-' + str(c.config.version) + '.tar.gz'
    package_path = 'dist/' + package
    put(c,package_path)
    sudo(c,'pip install %s --break-system-packages' % package)
    sudo(c,'rm -f %s' %(package))
     
@task
def undeploy(c):
    """Uninstall package on remote hosts(s)"""
    package = 'slacm'
    sudo(c,'pip uninstall -y %s --break-system-packages' % package)

@task
def wipe(c):
    """Wipe all user files on remote host(s)"""
    sudo(c,'rm -fr /home/%s/[a-zA-Z]*' % ctx.config.user)
    
@task
def requires(c):
    """Install requirements on remote host(s)"""
    put(c,"requirements.txt")
    sudo(c,"pip install -r requirements.txt --break-system-packages")
    run(c,'rm -f requirements.txt')
     
@task
def kill(c):
    """Kill any hanging processes"""
    sudo(c,"pkill -SIGKILL slacm_run")
     
@task
def stop(c):
    """Stop local slacm process"""
    run(c,"pkill -SIGTERM -f slacm_run")
    
@task
def shutdown(c):
    """Shutdown all hosts"""
    sudo(c,"shutdown now")
        
     