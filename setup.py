# Copyright 2016 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Setup script."""
import os.path
import re
from setuptools import setup, find_packages


def version():
    cur_dir = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(cur_dir, 'aiohttp_auth', '__init__.py'), 'r') as f:
        try:
            ver = re.findall(r"^__version__ = '([^']+)'\r?$",
                             f.read(), re.M)[0]
        except IndexError:
            raise RuntimeError('Could not determine version.')

        return ver


LONG_DESCRIPTION = '\n\n'.join((open('README.rst').read(),
                                open('CHANGELOG.rst').read()))

CLASSIFIERS = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: Apache Software License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: Implementation :: CPython",
    'Topic :: Database',
    'Topic :: Software Development :: Libraries :: Python Modules',
]

requires = [
    'pymodm==0.3.1.dev0',
    'motor==1.1.0'
]

setup(
    name='pymodm_motor',
    version=version(),
    author='ilex',
    author_email='ilexhostmaster@gmail.com',
    license='Apache License, Version 2.0',
    include_package_data=True,
    description='Pymodm_motor is an async ODM on top of PyMODM using Motor.',
    long_description=LONG_DESCRIPTION,
    packages=find_packages(exclude=['test', 'test.*']),
    platforms=['any'],
    classifiers=CLASSIFIERS,
    test_suite='test.get_test_suite',
    install_requires=requires,
    extras_require={'images': 'Pillow'}
)
