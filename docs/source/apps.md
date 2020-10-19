# SLACM Applications

The developer is expected to follow strict structure for the application. In the description 
below APP stands for the name of an application, and COMP* for some component. 

## Single host applications

An application packages should be created in a folder hierarchy as shown below.

```
APP/
   - APP.slacm (required)
   - COMP1.py  
   ....
   - COMPN.py  
   - APP.params (required if app expects parameters)
   - slacm.conf (optional)
   - slacm-log.conf 
   - other files for the application (source, data, etc.)
```

`APP.slacm` is the application model file, and `COMP1.py`... `COMPN.py` are the application components. 
The names of the components, and the component files **must** match the names used in the model. See the example below.

```
// App model
app HelloApp:
    message Msg
    
    component Hello2Pub:
      timer clock 1000
      pub port : Msg
    
    component Hello2Sub:
      sub port : Msg                  
    
    actor HelloActor:
       local Msg
       thePub : Hello2Pub
       theSub : Hello2Sub
...
```
Note the `local Msg` clause in the actor: this is a 'scoping' rule for the `Msg` messages. If this clause is present, 
messages of this topic are restricted to the host the actor is running on. This is useful in cases where messages generated 
on one hosts should not be distributed through the entire network. 

The two component files show examples for components, the implementation of message handlers, and the use of the ports. 

`Hello2Pub.py:`

```
from slacm.component import Component     # Must import base class

class Hello2Pub(Component):               # Must derive from Component
    def __init__(self, arg1,arg2=None):
        super().__init__()                # Base class initialization
        self.logger.info('-(%r,%r)' % (arg1,arg2))  # Python standard logger
        self.cnt = 0
    
    def on_clock(self):                   # Implements the message handler for `clock`
        now = self.clock.recv_pyobj()     # Must receive message (clock value)
        self.logger.info('on_clock(): %s', str(now))
        msg = "msg" + str(self.cnt)
        self.cnt += 1
        self.port.send_pyobj(msg)         # Send message out via 'port' 
        self.logger.info("send: %s" % msg)
```


`Hello2Sub.py:`

```
from slacm.component import Component

class Hello2Sub(Component):
    def __init__(self, arg3, arg4):
        super().__init__()
        self.logger.info('-(%r,%r)' % (arg3,arg4))
    
    def on_port(self):                    # Message handler for `port`
        msg = self.port.recv_pyobj()      # Must receive message
        self.logger.info('on_port(): recv = %s', msg)        
```

In addition to the application model, an optional parameter file (`APP.params`) can be added to the package. 
This file defines the values for the parameters of the component constructors (`arg1`, `arg2` in `Hello2Pub` 
and `arg3`,`arg4` in `Hello2Sub`). The is a [YAML](https://yaml.org/) file, which does not allow TAB-s, only spaces. 
In the file strict tabulation establishes a hierarchy, and the data types for values can be anything that YAML accepts. 
Example below shows the parameter file for the app.

```
# Single host version
root:
  HelloActor:
    thePub:
      arg1: "this is arg1"
#     arg2: use default for this one
    theSub:
      arg3: dir/file
      arg4: 1.23456
```
The file sets the parameter values for the application deployed on the `root` node (i.e. the host it is running on), 
for the specific actor (`HelloActor`), and the specific components (`thePub` and `theSub`). The parameters are 
identified by name. Note that `arg2` is optional (because the constructor has provided a default value. 

The model, the parameter and component files are sufficient for runnig an application using the `slacm_run` tool, as follows:

```
$ slacm_run APP.slacm 
```
Note that the application model did not have `host` clauses, i.e. this application is run on the host where the source code is located. 

**Note:** If the app needs to access physical devices, the above command should be started with a `sudo` prefix. 

The application can be terminated with a Ctrl-C (`SIGTERM`) on the terminal. 


## Distributed applications

The above application can be easily converted to a distributed one, where the two components run in separate actors, in separate hosts. 
(The hosts must have SLACM installed.) 

The application model is modified as follows:

```
app HelloApp:
    message Msg
    
   component Hello2Pub:
      timer clock 1000
      pub port : Msg
    
   component Hello2Sub:
      sub port : Msg                  
       
   actor PubActor:
      thePub : Hello2Pub  
   
   actor SubActor:
      theSub : Hello2Sub
     
 // Distributed version
     host (rpi4car) PubActor
     host root SubActor 

```
The root hosts runs the `SubActor` and the `rpi4car` runs the `PubActor`. For the latter, one can use the IP address of the specific
host as well. 

Because the application architecture has changed, the parameter file must be upated as well.

```
# root + rpi4car version
rpi4car:
   PubActor:
    thePub:
      arg1: "this is arg1"
#     arg2: use default for this one
root:
   SubActor:
    theSub:
      arg3: dir/file
      arg4: 1.23456
```

Now the same command can be executed (on the root):

```
$ slacm_run APP.slacm 
```

The (command running on *root*) will collect all the files in the application folder, transfers them to the *peer* node `rpi4car` and starts iself. The two `slacm_run` processes communicate with each other via the messages. 

**Note:** If the app needs to access physical devices, the above command should be started with a `sudo` prefix. 


# SLACM configuration for the application

There two, optional files in the application folder that provide configuration information for the application.

`slacm.conf` is for setting global parameters for SLACM intself. The file follows the `config` file syntax, as shown on the example 
below. The example is used for single host applications.

```
[SLACM]

# User name on remote hosts
target_user = slacm
# Timeout for send operations
send_timeout = 10000
# Timeout for recv operations
# recv_timeout = 1000

# NIC name
# Typical VM interface
nic_name = enp0s8
# Typical RPi interface   
# nic_name = eth0 
sudo = True
app_logs = std
```

The `target_user` specifies that name for the user accounts on the remote hosts, and the next two are for
setting timeouts on send and receive operations (in milliseconds). 

The `nic_name` parameter selects the network interface (as shown by the `ifconfig` command) used in accessing 
the network with the SLACM hosts. The value shown above is typical for development VM-s. 

The '`sudo` option (default: `True`) controls whether the remote hosts will run the application with root privileges. This is needed
if the application needs to access physical devices. Note that this value should go into the configuration of the host
the application is launched from. 

The `app_logs` option configures where to send the log messages produced by the component's loggers. 
The following values are possible:
- 'std': standard output
- 'log': logs are written into a file called `ACTOR.COMPONENT_NAME.TYPE_NAME.log`. 
- '' : logs are discarded

For multi-host deployments the configuration file can have multiple sections, one for each hosts. 
An example is shown below. 

```
# Section for all hosts
[SLACM]

# Timeout for send operations
send_timeout = 10000
# recv_timeout = 1000

# NIC name
# Typical VM interface
nic_name = enp0s8
# Typical RPi interface   
# nic_name = eth0  
sudo = True 
app_logs = std


# Section for host called `rpi4car`
[SLACM.rpi4car]

# Timeout for send operations
send_timeout = 10000
# recv_timeout = 1000

# NIC name
# Typical VM interface
# nic_name = enp0s8
# Typical RPi interface   
nic_name = eth0   
app_logs = std
```

Note the section marker identifying a host. 

`slacm-log.yaml` is for configuring the logging system. It requires intricate knowledge of the architecture of 
SLACM and the Python logging system, and it is subject, so it is not documented here. The default file is shown here, 
and it is useful for most applications.

```
# SLACM logging configuration file
version: 1
disable_existing_loggers: true

formatters:
  simpleFormatter:
    format: "%(levelname)s:%(asctime)s:[%(hostname)s.%(process)d]:%(name)s:%(message)s"
    # datefmt=
    default_time_format: "%H:%M:%S"
    default_msec_format: "%s,%03d"

filters:
  hostnameFilter:
    "()": "slacm.config.HostnameFilter"
  
handlers:
  consoleHandler:
    class: logging.StreamHandler
    level: INFO
    formatter: simpleFormatter
    filters: [hostnameFilter]
    stream: ext://sys.stdout

root:
  level: INFO
  propagate: 0
  handlers: [consoleHandler]
  
# SLAM loggers
#  slam_x:
#    level: INFO
#    propagate: 0
#    handlers: [console]
#    qualname: slam.x
```
The above configuration enables all `INFO` level logging in SLACM, and is recommended for use in application development. 



