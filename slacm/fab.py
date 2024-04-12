import os
from typing import List
from invoke import Program, Argument, Collection
from invoke.parser import Argument
from invoke.exceptions import Exit
from fabric import Executor, Config
from fabric.main import Fab
import slacm.tasks

ns = Collection()
slacm.tasks.namespace=ns
ns.add_collection(slacm.tasks,"do")

Config.user="slacm"
Config.connect_kwargs = { "key_filename": "/home/%s/.ssh/id_rsa" % os.getlogin() }
Config.version="0.0.2"

_program = Fab(namespace=ns,
                name="slacm_fab",
                executor_class=Executor,
                config_class=Config)
