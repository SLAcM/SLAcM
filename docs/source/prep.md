# Setting up SLACM

SLACM is distributed computing platform, and it runs a set of hosts connected via the network. For simplicity, all hosts are to be
located on the same sub-net. All hosts are expected to run Linux, to be specific Ubuntu 22.04  with Python 3.11 (or later) installed. 
One specific host, called the _development_ host is where all the application source code, model, configuration  and related data files, etc.
are located. Other hosts, called the _target_ hosts can run specific actors of the application. 

Target hosts are optional, so an application can run on the development host only, on target hosts only, or on any combination 
of the development and target hosts. If target hosts are used, they must have a special user (called 'slacm') that the SLACM 
framework is using to run application actors.

## Create the 'slacm' user on the target hosts

Create a user 'slacm' and add it to the 'sudo' capable users:
```
$ sudo adduser slacm
$ usermod -aG sudo username
```
Enable passwordless sudo for 'slacm'
```
sudo -s
echo "{slacm} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/slacm
```

## Set up the development host

Use the the **development** host to set up key-based/password-less access to all target hosts. 

- Generate a key-pair
```
$ ssh-keygen
```
- Copy the key-pair to each target host
```
$ ssh-copy-id slacm@TARGETIP
```
- Verify password-less access:
```
$ ssh slacm@TARGETIP
```
This last command should not ask for password.

Repeat the last two steps for each target host. 

## Install SLACM

On the **development** host: 

- Download the source distibution from the repository. 
```
$ git clone https://github.com/SLAcM/SLAcM.git
$ cd SLAcM
```
- Install required packages:
```
$ pip install -r requirements.txt --break-system-packages
```
Note: The recommended way to install Python packages is to use a Python Virtual Environment and install the packages there. 
However, the packages SLACM needs are not interfering with system packages, hence they can be safely installed. Hence the flag `--break-systemm-packages` option.

- Install SLACM itself:
```
$ sudo python3 setup.py install
```

## fab file

There is a [`fabfile`](https://www.fabfile.org) included in the package, that implements some useful commands, for interacting with the target hosts. These commands can be run using `fab` command in the source folder, where the fabfile is located.  


The `fabfile.py` contains the name of the remote target node, in the following line: 

```
 hosts = ['rpi4car']
 ```
When the fab commands are executed 

 The list has the hostnames (or IP address as a string) of all the target nodes. 
 
 The available commands are:
 - `fab check`: connects to the target nodes, and prints their system information
 - `fab requires`: installs the required 3rd party packages on all target nodes
 - `fab install`: installs SLACM on the local host - must be run with 'sudo'
 - `fab deploy`: installs SLACM on all target nodes
 - `fab uninstall`: unistalless SLACM from thelocal host - must be run with 'sudo'
 - `fab undeploy`: uninstalls SLACM on all target nodes
 
 - `fab stop`: stops a running SLACM application (`slacm_run`) on the host. 
 - `fab kill`: kills any lingering SLACM processes on all target nodes
 - `fab wipe`: wipe the 'slacm' user account clean on the target nodes

 
 Internal commands (for developer's use only):
 - `fab build`: rebuilds the SLACM package from source, on the local host 
 - `fab get`: retrieve a remote file from a target node
 - `fab put`: place a local file to a target node
 - `fab run`: run a command on a target node. Example: `fab run "ls -al"`
 - `fab sudo`: run a sudo command on a target node. Example: `fab sudo "ls -al /root"`

 