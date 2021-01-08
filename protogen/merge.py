#!/usr/bin/python3

import sys
import argparse
from lxml import etree

def cmp_nodes(node1, node2):
    if node1.tag != node2.tag:
        return False
    for attr in node2.keys():
        if node1.get(attr) and node1.get(attr)!=node2.get(attr):
            return False
    # all attributes of 2 were present and equal in 1
    return True

def parse_node(node1, node2):
    for sub2 in node2:
        for sub1 in node1:
            if cmp_nodes(sub1, sub2):
                # copy attributes from 2 to 1
                num = 0
                for attr in sub2.keys():
                    if sub1.get(attr) != sub2.get(attr):
                        sub1.attrib[attr] = sub2.get(attr)
                        num += 1
                parse_node(sub1, sub2)

def read_type(xml, fd):
    tname = xml.get('type-name')
    out = etree.XML("<%s type-name='%s' export='true'/>" % (xml.tag, tname))
    line = fd.readline()
    count = 0
    while line:
        if line[0] != '\t':
            break
        tokens = line.split()
        if not tokens:
            pass
        else:
            # look for field with same name
            fname = tokens[0]
            fields = xml.findall('.//*[@name="%s"]' % (fname))
            if not fields:
                method = 'get'+fname[0].upper()+fname[1:]
                fields = xml.findall('./virtual-methods/vmethod[@name="%s"]' % (method))
                if fields:
                    # FIXME: several vmethods are created ?!
                    vm = etree.SubElement(out, "virtual-methods")
                    elt = etree.XML("<vmethod name='%s'/>" % (method))
                    vm.append(elt)
            else:
                elt = etree.XML("<%s name='%s'/>" % (fields[0].tag, fname))
                out.append(elt)
            if not fields:
                sys.stderr.write('type %s: field <%s> not found\n' % (tname, fname))
            else:
                if len(tokens) == 1:
                    elt.set('export', 'true')
                elif len(tokens)==3 and tokens[1]=='as':
                    elt.set('export_as', tokens[2])
                else:
                    sys.stderr.write('error parsing line \'%s\'\n' % line)
                    continue
                count += 1
        line = fd.readline()
    sys.stderr.write('type %s: %d field(s) exported\n' % (tname, count))
    return out
    
def t2x(fd, xml):
    out = etree.XML("""<?xml version="1.0"?>
    <data-definition>
    </data-definition>
    """)
    line = fd.readline()
    while line:
        tokens = line.split()
        if tokens and line[0] != '\t':
            # look for type with same name
            elts = xml.findall('.//*[@type-name="%s"]' % (tokens[0]))
            if elts:
                out.append(read_type(elts[0], fd))
        line = fd.readline()
    return out

def text_to_xml(fname, xml):
    with open(fname, 'r') as fd:
        out = t2x(fd, xml)
    return out

def main():
    # parse args
    parser = argparse.ArgumentParser(description='Merge attributes of two xml trees.')
    parser.add_argument('input1', metavar='FILE1', type=str,
                        help='base xml file')
    parser.add_argument('input2', metavar='FILE2', type=str,
                        help='xml file to merge with base')
    parser.add_argument('--text', action='store_true', default=False,
                        help='FILE2 has \'export\' text format')
    args = parser.parse_args()
    
    # merge both trees starting from roots
    xml1 = etree.parse(args.input1).getroot()
    if args.text:
        xml2 = text_to_xml(args.input2, xml1)
    else:
        xml2 = etree.parse(args.input2).getroot()
    parse_node(xml1, xml2)

    # reexport base tree
    etree.ElementTree(xml1).write(sys.stdout.buffer, pretty_print=True)
    
if __name__ == "__main__":
    main()
