#!/usr/bin/env python3

# Output list of generated files

import traceback
import sys
import argparse
import os
import glob
from lxml import etree


def main():
    
    # parse args
    parser = argparse.ArgumentParser(description='Output list of files generated from dfhack structures.')
    parser.add_argument('input', metavar='INDIR', type=str,
                        default='./', help='input directory or file (default=.)')
    parser.add_argument('output', metavar='OUTDIR', type=str,
                        default='./protogen', help='output directory (default=./protogen)')
    parser.add_argument('--type', metavar='TYPE', type=str,
                        default='proto', help='type proto|h|cpp (default=proto)')
    parser.add_argument('--separator', metavar='SEP', type=str,
                        default='\n', help='separator (default=\n)')
    parser.add_argument('--filter', metavar='FILT', type=str,
                        default=None, help='filter (default=*)')
    args = parser.parse_args()

    # input dir
    indir = args.input
    assert os.path.exists(indir), indir
    if not indir.endswith('/'):
        indir += '/'
    
    # output dir
    outdir = args.output
    if not os.path.exists(outdir):
        os.mkdir(outdir)
        print('created ' + outdir)
    if not outdir.endswith('/'):
        outdir += '/'

    # collect types and convert to filenames
    if args.filter:
        filt = indir + args.filter
    else:
        filt = indir+'df.*.xml'
    rc = 0
    for f in glob.glob(filt):
        xml = etree.parse(f)
        for item in xml.getroot():
            try:
                tname = item.get('type-name')
                if item.tag not in ['struct-type', 'class-type', 'enum-type', 'bitfield-type', 'df-linked-list-type']:
                    continue
                if not tname:
                    continue
                if args.type == 'proto':
                    sys.stdout.write(outdir+tname+'.proto'+args.separator)
                    continue
                if item.tag not in ['struct-type', 'class-type', 'df-linked-list-type']:
                    continue
                sys.stdout.write(outdir+tname+'.'+args.type+args.separator)
            except Exception as e:
                _,_,tb = sys.exc_info()
                sys.stderr.write('error parsing type %s at line %d: %s\n' % (tname, item.sourceline if item.sourceline else 0, e))
                traceback.print_tb(tb)
                sys.exit(1)


if __name__ == "__main__":
    main()
