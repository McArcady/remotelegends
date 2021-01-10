#!/usr/bin/python3

import sys
import argparse
from lxml import etree

def parse_type(xml, fd):
    tname = xml.get('type-name')
    xml.set('export', 'true')
    pos = fd.tell()
    line = fd.readline()
    count = 0
    warnings = 0
    while line:
        if line[0] != '\t':
            fd.seek(pos)
            break
        tokens = line.split()
        if tokens and tokens[0][0] != '#':
            # look for field with same name
            fname = tokens[0]
            fields = xml.findall('./*[@name="%s"]' % (fname))
            if not fields:
                # look for method
                method = 'get'+fname[0].upper()+fname[1:]
                fields = xml.findall('./virtual-methods/vmethod[@name="%s"]' % (method))
            if len(fields) > 1:
                sys.stderr.write('warning: %d elements found for field name <%s>\n' % (len(fields), fname))
                warnings += 1
            if fields:
                elt = fields[0]
                if len(tokens) == 1:
                    for sub in elt.iter():
                        sub.set('export', 'true')                        
                elif len(tokens)==3 and tokens[1]=='as':
                    elt.set('export-as', tokens[2])
                else:
                    sys.stderr.write('error parsing line \'%s\'\n' % line)
                    raise Error(line)
                count += 1
            else:
                sys.stderr.write('type %s: field <%s> not found\n' % (tname, fname))
                warnings += 1
        pos = fd.tell()
        line = fd.readline()
    sys.stderr.write('type %s: %d field(s) exported\n' % (tname, count))
    return warnings
    
def parse_structure(fd, xml):
    line = fd.readline()
    warnings = 0
    while line:
        tokens = line.split()
        if tokens and tokens[0][0] != '#' and line[0] != '\t':
            # look for type with same name
            tname = tokens[0]
            types = xml.findall('./*[@type-name="%s"]' % (tname))
            if len(types) > 1:
                sys.stderr.write('warning: %d elements found for type name <%s>\n' % (len(types), tname))
                warnings += 1
            if types:
                warnings += parse_type(types[0], fd)
            else:
                sys.stderr.write('type <%s> not found\n' % (tname))
                warnings += 1
        line = fd.readline()
    return warnings

def main():
    # parse args
    parser = argparse.ArgumentParser(description='Declare exported fields in DF structure.')
    parser.add_argument('input1', metavar='FILE1', type=str,
                        help='DF structure xml file')
    parser.add_argument('input2', metavar='FILE2', type=str,
                        help='description of exported elements')
    args = parser.parse_args()
    
    # parse xml and add export attributes
    xml = etree.parse(args.input1).getroot()
    with open(args.input2, 'r') as fd:
        warnings = parse_structure(fd, xml)

    if warnings > 0:
        sys.exit(1)

    # reexport base tree
    etree.ElementTree(xml).write(sys.stdout.buffer, pretty_print=True)

if __name__ == "__main__":
    main()
