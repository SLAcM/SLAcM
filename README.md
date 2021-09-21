# Simple Lightweight Actor Model (SLACM)

SLACM is a small application framework for distributed, component-based applications. It is based on [ZeromMQ](https://zeromq.org) and implemented [Python](https://www.python.org). SLACM applications are built from *components* (objects that run in their own, distinct thread), that are grouped together into *actors* (processes), that are deployed on *hosts* (computing nodes on a network). The components interact *only* via messages, via the framework.  The components are *reactive* and are scheduled by the framework; they are triggered bye events: either the arrival of a message or a timer tick. The supported component interactions include both the publish-subscribe and the remote procedure call paradigms. The application components form an architecture that is explicitly specified in the form of an application model, that also decsribes how the application (actors) are to be deployed on a network. 

Documentation is at https://slacm.readthedocs.io/


