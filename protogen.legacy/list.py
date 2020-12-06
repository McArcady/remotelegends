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
    parser = argparse.ArgumentParser(description='Output list of files generated from a DFHack XML structure.')
    parser.add_argument('input', metavar='INFILE', type=str, help='DFHack structure XML file')
    parser.add_argument('output', metavar='OUTDIR', type=str, nargs='?', 
                        default='./protogen', help='target directory for generated files (default=./protogen)')
    parser.add_argument('--type', metavar='TYPE', type=str,
                        default='proto', help='type proto|h|cpp (default=proto)')
    parser.add_argument('--separator', metavar='SEP', type=str,
                        default='\n', help='separator (default=\n)')
    args = parser.parse_args()

    # input dir
    infile = args.input
    assert os.path.exists(infile), infile
    
    # output dir
    outdir = args.output
    if outdir and not outdir.endswith('/'):
        outdir += '/'
    else:
        outdir = ''

    # collect types and convert to filenames
    rc = 0
    xml = etree.parse(infile)
    for item in xml.getroot():
        try:
            tname = item.get('type-name')
            if item.tag not in ['struct-type', 'class-type', 'enum-type', 'bitfield-type', 'df-linked-list-type']:
                continue
            if not tname:
                continue
            if item.get('export') != 'true':
                continue
            if args.type == 'proto':
                sys.stdout.write(outdir+tname+'.proto'+args.separator)
                continue
            if item.tag not in ['struct-type', 'class-type', 'bitfield-type', 'df-linked-list-type']:
                continue
            sys.stdout.write(outdir+tname+'.'+args.type+args.separator)
        except Exception as e:
            _,_,tb = sys.exc_info()
            sys.stderr.write('error parsing type %s at line %d: %s\n' % (tname, item.sourceline if item.sourceline else 0, e))
            traceback.print_tb(tb)
            sys.exit(1)


if __name__ == "__main__":
    main()
