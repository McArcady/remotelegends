#!/usr/bin/env python3
#
# Generate and compile proto files with:
# $ ./protogen.py  ../df-structures && for f in $(ls protogen/*.proto); do echo $f &&  protoc -Iprotogen/ -otest.pb $f ||  break; done
#

import traceback
import sys
import argparse
import re
import os
import glob
from lxml import etree

from global_type_renderer import GlobalTypeRenderer

COLOR_OKBLUE = '\033[94m'
COLOR_FAIL = '\033[91m'
COLOR_ENDC = '\033[0m'


def main():
    
    # parse args
    parser = argparse.ArgumentParser(description='Generate protobuf and conversion code  from dfhack structures.')
    parser.add_argument('input', metavar='DIR|FILE', type=str,
                        help='input directory or xml file (default=.)')
    parser.add_argument('--proto_out', metavar='PROTODIR', type=str,
                        default='./protogen',
                        help='output directory for protobuf files (default=./protogen)')
    parser.add_argument('--cpp_out', metavar='CPPDIR', type=str,
                        default='./protogen',
                        help='output directory for c++ files (default=./protogen)')
    parser.add_argument('--h_out', metavar='HDIR', type=str,
                        default='./protogen',
                        help='output directory for c++ headers (default=./protogen)')
    parser.add_argument('--version', '-v', metavar='2|3', type=int,
                        default='2', help='protobuf version (default=2)')
    parser.add_argument('--quiet', '-q', action='store_true',
                        default=False, help='no output (default: False)')
    args = parser.parse_args()

    # input dir
    indir = args.input
    assert os.path.exists(indir)
    if os.path.isdir(indir) and not indir.endswith('/'):
        indir += '/'
    
    # output dir
    for outdir in [args.proto_out, args.cpp_out, args.h_out]:
        if not os.path.exists(outdir):
            os.mkdir(outdir)
            if not args.quiet:
                sys.stdout.write('created %s\n' % (outdir))

    # xml with all types
    outxml = open(args.proto_out+'/protogen.out.xml', 'wb')

    # collect types
    transforms = [
        etree.XSLT(etree.parse(os.path.dirname(indir)+'/'+f)) for f in ['lower-1.xslt', 'lower-2.xslt']
    ]
    filt = indir
    if os.path.isdir(indir):
        filt = indir+'df.*.xml'
    rc = 0
    for f in glob.glob(filt):
        if not args.quiet:
            sys.stdout.write(COLOR_OKBLUE + 'processing %s...\n' % (f) + COLOR_ENDC)
        xml = etree.parse(f)
        for t in transforms:
            xml = t(xml)
        ns = re.match(r'{(.*)}', xml.getroot().tag).group(1)
        xml.write(outxml)
        for item in xml.getroot():
            try:
                if 'global-type' not in item.tag:
                    if not args.quiet:
                        sys.stdout.write('skipped global-object '+item.get('name') + '\n')
                    continue
                rdr = GlobalTypeRenderer(item, ns)
                rdr.set_proto_version(args.version)
                fnames = rdr.render_to_files(args.proto_out, args.cpp_out, args.h_out)
                if not args.quiet:
                    sys.stdout.write('created %s\n' % (', '.join(fnames)))
            except Exception as e:
                _,_,tb = sys.exc_info()
                sys.stderr.write(COLOR_FAIL + 'error rendering type %s at line %d: %s\n' % (rdr.get_type_name(), item.sourceline if item.sourceline else 0, e) + COLOR_ENDC)
                traceback.print_tb(tb)
                rc = 1
                break
        if rc:
            break

    outxml.close()
    if not args.quiet:
        sys.stdout.write('created %s\n' % (outxml.name))
    sys.exit(rc)


if __name__ == "__main__":
    main()
