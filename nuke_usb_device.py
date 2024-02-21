#!/usr/bin/env python3

import os, fcntl, re, subprocess, argparse


USBDEVFS_RESET = ord('U') << (4*2) | 20

KNOWN_DEVICES = {
    'fwd': {
        '0403:6001': 'FT232',
        '0403:6011': 'FT4232',
        '0403:6015': 'FT230X',
    },
}
KNOWN_DEVICES['rev'] = { v: k for k,v in KNOWN_DEVICES['fwd'].items() }

class USB_Nuker():
    def __init__(self):
        self.devices = self.__makeDeviceDict()

    def getMatching(self, vendor, product):
        return self.devices.get(vendor,{}).get(product,[])

    def asPaths(self, busdevs):
        return [ f"/dev/bus/usb/{bd['bus']:03d}/{bd['device']:03d}" for bd in busdevs ]
 
    def __makeDeviceDict(self):
        p = subprocess.Popen(['lsusb'], stdout=subprocess.PIPE)
        lines = p.communicate()[0].decode('ascii').splitlines()
        rv = {}
        for line in lines:
            m = re.search(r'Bus (\d{3}) Device (\d{3}): ID ([\dabcdef]{4}):([\dabcdef]{4}) (.*)$', line)
            if m:
                bus     = int(m[1]);
                dev     = int(m[2]);
                vendor  = int(m[3],16);
                product = int(m[4],16);
                descr   = m[5]
                if not vendor in rv:
                    rv[vendor] = {}
                if not product in rv[vendor]:
                    rv[vendor][product] = []
                         
                rv[vendor][product].append({
                    'bus': bus, 'device': dev, 'description': descr,
                })
        return rv

    def nukePath(self, path):
        try:
            fd = os.open(path, os.O_WRONLY)
            fcntl.ioctl(fd, USBDEVFS_RESET, 0);
        except Exception as e:
            print(f'got {repr(e)} trying to reset {path}')


    def run(self, args):
        busdev_str = KNOWN_DEVICES['rev'].get(args.device,args.device)
        m = re.search(r'([\dabcdef]{4}):([\dabcdef]{4})', busdev_str)
        if m:
            vendor  = int(m[1],16)
            product = int(m[2],16)
            paths = self.asPaths(self.getMatching(vendor, product))
            for p in paths:
                print(f'Nuking: {busdev_str} as {p}')
                self.nukePath(p)

    def getArgs(self):
        
        def makeTables():
            rv = {
                'options': [],
                'formatted': [
                    'Known device table:',
                    '    -------------------- | ---------------------------------',
                ],
            }
            for vendor in self.devices:
                for product in self.devices[vendor]:
                    combined_str = f'{vendor:04x}:{product:04x}' 
                    combined_str = KNOWN_DEVICES['fwd'].get(combined_str, combined_str)
                    rv['formatted'].append(f"    {combined_str:20} | {self.devices[vendor][product][0]['description']}")
                    rv['options'].append(combined_str)
            rv['formatted'].append('')
            return rv 

        tables = makeTables()
        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter,
            description="Utility to reset a USB device by the vendor and product id",
            prog='USB Device Nuker',
            epilog='\n'.join(tables['formatted'])
        )

        parser.add_argument(
            '--device', '-d',
            help='device to reset',
            required=True,
            choices=tables['options']
        )
        return parser.parse_args()



if __name__ == '__main__':
    n = USB_Nuker()
    n.run(n.getArgs())
