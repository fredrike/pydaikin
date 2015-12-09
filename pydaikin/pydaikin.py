#!/usr/bin/env python

import httpentity
import discovery
import time
import argparse

parser = argparse.ArgumentParser(description = 'Daikin wireless interface.')

group = parser.add_mutually_exclusive_group(required = True)

group.add_argument('device', metavar='dev', nargs='?',
                   help='device, either ip or common name')

group.add_argument('-l', '--list', action='store_true',
                   help='list all the devices found')

parser.add_argument('-a', '--all', action='store_true',
                    help='show all the values available for the device')

parser.add_argument('-p', '--power',
                    help='turn on or off the device')

args = parser.parse_args()

if args.list:
    for dev in discovery.get_devices():
        print "%18s: %s" % (dev['ip'], dev['name'])

else:
    e = httpentity.HttpEntity(args.device)
    if not args.all:
        only_summary = True
    else:
        only_summary = False

    e.show_values(only_summary)
