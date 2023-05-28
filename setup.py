# -*- coding: utf-8 -*-
from setuptools import setup

packages = \
['nuvoprogpy']

package_data = \
{'': ['*']}

setup_kwargs = {
    'name': 'nuvoprogpy',
    'version': '0.1.0',
    'description': 'In-Chip Programmer and In System Programmer libraries for the N76E003 microcontroller',
    'long_description': "# nuvoprog\n\nThis is a port of Steve Markgraf's excellent N76 programming tools to the Arduino platform.  See Steve's original work here: https://github.com/steve-m/N76E003-playground\n\nTested on: Lolin(WeMOS) D1 mini @ 80MHz: 1 cycle = 12.5ns\n\tDAT:   D1\n\tCLK:   pinD2\n\tRST:   D3\n",
    'author': 'nikitalita',
    'author_email': '69168929+nikitalita@users.noreply.github.com',
    'maintainer': 'None',
    'maintainer_email': 'None',
    'url': 'None',
    'packages': packages,
    'package_data': package_data,
    'python_requires': '>=3.9',
}

from build import *
build(setup_kwargs)
setup(**setup_kwargs)
