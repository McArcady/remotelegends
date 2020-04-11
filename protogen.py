#!/usr/bin/env python3

import copy
import sys
import argparse
import re
import os
import glob
from lxml import etree

from global_type_renderer import GlobalTypeRenderer


def main(argv=sys.argv):
    
    # parse args
    parser = argparse.ArgumentParser(description='Generate proto3 from dfhack structures.')
    parser.add_argument('input', metavar='DIR|FILE', type=str, nargs='?',
                        default='./', help='input directory or file (default=.)')
    parser.add_argument('--output', '-o', metavar='OUTPUT', type=str,
                        default='./protogen',
                        help='output directory (default=./protogen)')
    args = parser.parse_args()
    print(str(args))

    # input dir
    indir = args.input
    assert os.path.exists(indir)
    if os.path.isdir(indir) and not indir.endswith('/'):
        indir += '/'
    
    # output dir
    outdir = args.output
    if not outdir.endswith('/'):
        outdir += '/'
    if not os.path.exists(outdir):
        os.mkdir(outdir)
        print('created ' + outdir)

    # xml with all types
    outxml = open(outdir+'protogen.out.xml', 'wb')

    # collect types
    transforms = [
        etree.XSLT(etree.parse(os.path.dirname(indir)+'/'+f)) for f in ['lower-1.xslt', 'lower-2.xslt']
    ]
    filt = indir
    if os.path.isdir(indir):
        filt = indir+'df.*.xml'
    for f in glob.glob(filt):
        print('processing %s...' % (f))
        xml = etree.parse(f)
        for t in transforms:
            xml = t(xml)
        ns = re.match(r'{(.*)}', xml.getroot().tag).group(1)
        print (ns)
        xml.write(outxml)
        for item in xml.getroot():
            rdr = GlobalTypeRenderer(item, ns)
            fname = rdr.render_to_file(outdir)
            print('created %s' % (outdir+fname))
    outxml.close()
    print('created %s' % (outxml.name))

    
if __name__ == "__main__":
    main()
