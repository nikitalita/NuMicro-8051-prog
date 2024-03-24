import platform
if platform.system() != 'Linux':
    raise NotImplementedError("%s is not supported yet" % platform.system())
from . import nuvo51icpy
from .nuvo51icpy import *
