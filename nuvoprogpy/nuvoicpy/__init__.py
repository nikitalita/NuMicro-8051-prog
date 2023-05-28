import platform
if platform.system() != 'Linux':
    raise NotImplementedError("%s is not supported yet" % platform.system())
from . import nuvoicpy
from .nuvoicpy import *
