# Setting up SLACM

SLACM is distributed computing platform, and it runs a set of hosts connected via the network. For simplicity, all hosts are to be
located on the same sub-net of a network. All hosts are expected to run Linux, to be specific Ubuntu 22.04  with Python 3.11 (or later) installed. 
The host can be Linux machine, a Linuc virtual machine, a WSL instance running on Windows, or an embedded system running Linux. 
One specific host, called the _development_ host is where all the application source code, model, configuration  and related data files, etc.
are located. Other hosts, called the _target_ hosts can run specific actors of the application. 

Target hosts are optional, so an application can run on the development host only, on target hosts only, or on any combination 
of the development and target hosts. If target hosts are used, they must have a special user (called 'slacm') that the SLACM 
framework is using to run application actors.

## Install SLACM

On the **development** host: 

- Download the source distibution from the repository. 
```
$ git clone https://github.com/SLAcM/SLAcM.git
$ cd SLAcM
```
- Install the packages required by SLACM:
```
$ pip install -r requirements.txt --break-system-packages
```
*Note*: The recommended way to install Python packages is to use a Python Virtual Environment and install the packages in there. 
However, the packages SLACM needs are not interfering with typical system packages, hence they can be safely installed. Hence the 
The  `--break-systemm-packages` option in the above command. This option should be omitted if the installation is for a Python virtual 
environment.

- Install SLACM itself:
```
$ cd SLAcM
$ sudo pip install .
```
*Note*: SLACM can be installed and used on the development host using any user name. However, if distributed applications are developed
then a 'slacm' user account must be created on the target hosts. SLACM will download the applications to the target using that account, and will
run them under that user. 

## Preparing the target hosts

### Create the 'slacm' user on the target hosts

Create a user 'slacm' and add it to the 'sudo' capable users:
```
$ sudo adduser slacm
$ usermod -aG sudo username
```
Enable passwordless sudo for 'slacm' on the target hosts

```
$ sudo -s
$ echo "{slacm} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/slacm
```

### Set up the target hosts for password-less access 

Use the the **development** host to set up key-based/password-less, key-based access to all target hosts. 

- Generate a key-pair, without password, on the _development_ host. 

```
$ ssh-keygen
```
*Note:* The generated key pair is expected to have the name `id_rsa` and `ida_rsa.pub`, and is to be located the 
`~/.ssh/` folder. 

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


## slacm_fab commands

There is a [`Fabric`](https://www.fabfile.org) script included in the package, that implements some useful commands, for interacting with the target hosts. These commands can be run using `slacm_fab` script in the source folder, where the fabfile is located. The script accepts the same arguments as the basic `fab` script. 

Example:

```
$ slacm_fab -H host1,host2 -v do.check
```
The arguments for the `-H` option specifies on which target host(s) the command `do.check` is to be executed. The `-v` option turns on logging.  
Commands on the remote hosts are running under the `slacm` user name. 

 The available commands are:
 - `do.check`: connects to the target nodes, and prints their system information
 - `do.requires`: installs the required 3rd party packages on the target nodes
 - `do.install`: installs SLACM on the local *development* host - must be run with 'sudo', and from the folder containing the `SLAcM' code base.
 - `do.deploy`: installs SLACM on *target* nodes - must be run from the folder containing the `SLAcM' code base.
 - `do.uninstall`: unistalless SLACM from the local *development* host - must be run with 'sudo'
 - `do.undeploy`: uninstalls SLACM from the target hosts
 
 - `do.stop`: stops a running SLACM application (`slacm_run`) on the target hosts
 - `do.kill`: kills any lingering SLACM processes on all target nodes
 - `do.wipe`: wipe the 'slacm' user account clean on the target nodes

  Internal commands (for developer's use only):
 - `do.build`: rebuilds the SLACM package from source, on the local host 
 - `do.get`: retrieve a remote file from a target node
 - `do.put`: place a local file to a target node
 - `do.run`: run a command on a target node. Example: `slacm_fab -H HOST do.run "ls -al"`
 - `do.sudo`: run a sudo command on a target node. Example: `slacm_fab -H HOST do.sudo "ls -al /root"`

 