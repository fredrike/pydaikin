#!/usr/bin/env python3

from setuptools import setup

setup(
    name='pydaikin',
    version='0.9',
    description='Python Daikin HVAC appliances interface',
    author='Yari Adan',
    author_email='mustang@yadan.org',
    license='GPL',
    url='https://bitbucket.org/mustang51/pydaikin',
    python_requires='>3.5',
    packages=['pydaikin'],
    keywords=['homeautomation', 'daikin'],
    install_requires=['netifaces', 'requests'],
    scripts=['bin/pydaikin'],
)
