#!/bin/python3

import unittest
import mock
import re
import subprocess
from lxml import etree

from cpp_renderer import CppRenderer

OUTPUT_FNAME = 'output.cpp'

class TestCppRenderer(unittest.TestCase):

    output = ''

    @classmethod
    def setUpClass(cls):
        pass
    
    def setUp(self):
        self.sut = CppRenderer('ns', 'dfproto', 'DFProto')
        self.maxDiff = None

    @classmethod
    def tearDownClass(cls):
        if not cls.output:
            return
        with open(OUTPUT_FNAME, 'a') as fil:
            fil.write(cls.output)
        subprocess.check_call(['protoc -I. -o%s.pb  %s' % (OUTPUT_FNAME, OUTPUT_FNAME)], shell=True)
        os.remove(OUTPUT_FNAME)
        os.remove(OUTPUT_FNAME+'.pb')

    def assertStructEqual(self, str1, str2):
        self.assertEqual(''.join(str1.split()), ''.join(str2.split()), str1+'/'+str2)

    
    #
    # test exceptions
    #

    def test_rename_field(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="struct-type" ld:level="0" type-name="entity_position_raw">
          <ld:field name="squad_size" ld:level="1" ld:meta="number" ld:subtype="int16_t" ld:bits="16"/>
        </ld:global-type>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        self.sut.add_exception_rename('ld:global-type[@type-name="entity_position_raw"]/ld:field[@name="squad_size"]', 'squad_sz')
        out = self.sut.render_type(root[0])
        self.assertStructEqual(out, """
        void DFProto::describe_entity_position_raw(dfproto::entity_position_raw* proto, df::entity_position_raw* dfhack) {
          proto->set_squad_sz(dfhack->squad_size);
        }
        """)


    #
    # prototype
    #
    
    def test_render_prototype(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:global-type ld:meta="bitfield-type" ld:level="0" type-name="announcement_flags">
          </ld:global-type>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_prototype(root[0])
        self.assertEqual(len(self.sut.imports), 0)
        self.assertStructEqual(out, """
        void describe_announcement_flags(dfproto::announcement_flags* proto, df::announcement_flags* dfhack);
        """)
        self.output += out + '\n'

        
    def _test_debug(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="class-type" ld:level="0" type-name="viewscreen_selectitemst" inherits-from="viewscreen">
        <ld:field ld:level="1" ld:meta="pointer" since="v0.47.02" ld:is-container="true"/>
        </ld:global-type>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_type(root[0])
        print(self.sut.imports)
        print(out)
        self.assertEqual(len(self.sut.imports), 0)
        self.assertStructEqual(out, """
        void describe_announcement_flags(dfproto::announcement_flags* proto, df::announcement_flags* dfhack);
        """)
        self.output += out + '\n'
        
       

    def _test_render_global_types(self):
        tree = etree.parse('codegen/codegen.out.xml')
        root = tree.getroot()
        ns = re.match(r'{.*}', root.tag).group(0)
        sut = ProtoRenderer(ns)
        
        for e in root:
            print( 'line '+str(e.sourceline)+':', e.get(f'{ns}meta'), e.get(f'type-name') )
            out = sut.render_type(e)
            self.output += out + '\n'
