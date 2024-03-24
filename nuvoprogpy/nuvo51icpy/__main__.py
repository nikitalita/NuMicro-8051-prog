import platform
if platform.system() != 'Linux':
    raise NotImplementedError("%s is not supported yet" % platform.system())
import sys

from .nuvo51icpy import main

try:
    if __name__ == "__main__":
        sys.exit(main())
except Exception as e:
    print("%s" % e)
    sys.exit(2)
