#!/usr/bin/env python

from distutils.core import setup

setup(name='pydaikin',
      version='0.1',
      description='Python Daikin HVAC appliances interface',
      author='Yari Adan',
      author_email='mustang@yadan.org',
      license='GPL',
      url='https://bitbucket.org/mustang51/pydaikin',
      packages=['pydaikin'],
      keywords=['homeautomation', 'daikin'],
      install_requires=['netifaces', 'requests'],
      scripts=['bin/pydaikin']
     )
