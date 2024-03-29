import platform
import sys

from .nuvoispy import main

try:
    if __name__ == "__main__":
        sys.exit(main())
except Exception as e:
    print("%s" % e)
    sys.exit(2)
