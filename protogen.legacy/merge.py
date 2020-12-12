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

def main():
    # parse args
    parser = argparse.ArgumentParser(description='Merge attributes of two xml trees.')
    parser.add_argument('input1', metavar='FILE1', type=str,
                        help='base xml file')
    parser.add_argument('input2', metavar='FILE2', type=str,
                        help='xml file to merge with base')
    args = parser.parse_args()
    
    # merge both tree starting from roots
    xml1 = etree.parse(args.input1)
    xml2 = etree.parse(args.input2)
    parse_node(xml1.getroot(), xml2.getroot())

    # reexport base tree
    etree.ElementTree(xml1.getroot()).write(sys.stdout.buffer, pretty_print=True)
    
if __name__ == "__main__":
    main()
