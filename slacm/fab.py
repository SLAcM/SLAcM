from typing import List
from invoke import Program, Argument, Collection
from invoke.parser import Argument
from invoke.exceptions import Exit
from fabric import ThreadingGroup, Config
import slacm.tasks

ns = Collection()
slacm.tasks.namespace=ns
ns.add_collection(slacm.tasks,"do")

_program = Program(namespace=ns)
