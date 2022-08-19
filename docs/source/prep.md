# Setting up SLACM


## Create the 'slacm' user on the target hosts

Add user 'slacm' and add it to the 'sudo' capable users:
```
$ sudo adduser slacm
$ usermod -aG sudo username
```
Enable passwordless sudo for 'slacm'
```
sudo -s
echo "{slacm} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/slacm
```

## Set up the development host (VM)

On the **development host**:
1) Add a 'bridged network adapter' to the VM: 
   - See VM/Settings/Network, add a new 'Bridged adapter'
   
2) Set up key-based/password-less access to target
   - Generate key-pair, copy key-pair to target:
```
$ ssh-keygen
$ ssh-copy-id slacm@TARGETIP
```
   - Verify password-less access:
```
$ ssh slacm@TARGETIP
```
This last command should not ask for password.


## Install SLACM

On the **development host**: 

Download the source distibution from the repository. 

```
$ git clone https://github.com/SLAcM/SLAcM.git
$ cd SLAcM
```

Install required packages:

```
$ pip3 install -r requirements.txt
```

Install SLACM itself:

```
$ sudo python3 setup.py install
```

## fab file

There is a [`fabfile`](https://www.fabfile.org) included in the package, that implements some useful commands, mainly for interacting with the target hosts. These commands can be run using `fab` command in the source folder, where the fabfile is located.  The `fabfile.py` contains the name of the remote target node, in the following line: 

```
 hosts = ['rpi4car']
 ```

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

 