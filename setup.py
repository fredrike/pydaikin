#!/usr/bin/env python3

from setuptools import setup

setup(
    name='pydaikin',
    version='1.4.4',
    description='Python Daikin HVAC appliances interface',
    author='Yari Adan',
    author_email='mustang@yadan.org',
    license='GPL',
    url='https://bitbucket.org/mustang51/pydaikin',
    python_requires='>3.5',
    packages=['pydaikin'],
    keywords=['homeautomation', 'daikin'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Home Automation",
    ],
    install_requires=['netifaces', 'aiohttp'],
    scripts=['bin/pydaikin'],
)
