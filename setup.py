#!/usr/bin/env python3

from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='pydaikin',
    version='2.1.1',
    description='Python Daikin HVAC appliances interface',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Yari Adan',
    author_email='mustang@yadan.org',
    maintainer=', '.join(
        (
            'Fredrik Erlandsson <fredrik.e+pydaikin@gmail.com>',
            'Matthias Lemainque <matthias.lemainque+pydaikin@gmail.com>',
        )
    ),
    license='GPL',
    url='https://bitbucket.org/mustang51/pydaikin',
    python_requires='>=3.6',
    packages=['pydaikin'],
    keywords=['homeautomation', 'daikin'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Home Automation",
    ],
    install_requires=['netifaces', 'aiohttp', 'urllib3'],
    tests_require=['pytest', 'pytest-aiohttp', 'freezegun'],
    scripts=['bin/pydaikin'],
)
