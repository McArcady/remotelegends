#!/bin/python3

import unittest
import mock
import subprocess
import xml.etree.ElementTree as ET

from renderer import Renderer

OUTPUT_FNAME = 'output.proto'

class TestRender(unittest.TestCase):

    output = ''

    @classmethod
    def setUpClass(cls):
        with open(OUTPUT_FNAME, 'w') as fil:
            fil.write('syntax = "proto3";\n')
            
    def setUp(self):
        self.sut = Renderer()

    def tearDown(self):
        with open(OUTPUT_FNAME, 'a') as fil:
            fil.write(self.output)

    @classmethod
    def tearDownClass(cls):
        subprocess.check_call(['protoc -I. -o%s.bp  %s' % (OUTPUT_FNAME, OUTPUT_FNAME)], shell=True)

    def assertStructEqual(self, str1, str2):
        self.assertEqual(''.join(str1.split()), ''.join(str2.split()), str1+'/'+str2)
    
    def test_render_enum_type(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:global-type ld:meta="enum-type" ld:level="0" type-name="ui_advmode_menu" base-type="int16_t">
            <enum-item name="Default" value="0"/>
            <enum-item name="Look"/>
          </ld:global-type>
        </ld:data-definition>
        """
        root = ET.fromstring(XML)
        out = self.sut.render(root[0])
        self.assertStructEqual(out, """
        enum ui_advmode_menu {
          Default = 0;
          Look = 1;
        }
        """)
        self.output += out + '\n'

    def test_render_enum(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:subtype="enum" base-type="int32_t" name="state" ld:level="1" ld:meta="compound" ld:typedef-name="T_state">
            <enum-item name="started"/>
            <enum-item name="active"/>
          </ld:field>
        </ld:data-definition>
        """
        root = ET.fromstring(XML)
        out = self.sut.render(root[0])
        self.assertStructEqual(out, """
        enum T_state {
          started = 0;
          active = 1;
        }
        T_state state = 1;
        """)
    
    def test_render_container(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:meta="container" ld:level="1" ld:subtype="stl-vector" type-name="int16_t" name="talk_choices" ld:is-container="true"><ld:item ld:level="2" ld:meta="number" ld:subtype="int16_t" ld:bits="16"/></ld:field>
        </ld:data-definition>
        """
        root = ET.fromstring(XML)
        out = self.sut.render(root[0])
        self.assertStructEqual(out, """
        repeat int32 talk_choices;
        """)
        
    def test_render_struct_type(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="struct-type" ld:level="0" type-name="conversation">
          <ld:field name="conv_title" ld:level="1" ld:meta="primitive" ld:subtype="stl-string"/>
          <ld:field name="unk_30" ref-target="unit" ld:level="1" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
        </ld:global-type>
        </ld:data-definition>        
        """
        root = ET.fromstring(XML)
        out = self.sut.render(root[0])
        self.assertStructEqual(out, """
        message conversation {
          string conv_title = 1;
          int32 unk_30 = 2;
        }
        """)
        self.output += out + '\n'

    def test_render_anon_compound(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:anon-compound="true" ld:level="3" ld:meta="compound">
            <ld:field name="x" ld:level="3" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
            <ld:field name="y" ld:level="3" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
          </ld:field>
        </ld:data-definition>    
        """
        root = ET.fromstring(XML)
        out = self.sut.render(root[0])
        self.assertStructEqual(out, """
        message T_anon {
          int32 x = 1;
          int32 y = 2;
        }
        """)
        self.output += out + '\n'

    def test_render_union(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:anon-compound="true" is-union="true" ld:level="3" ld:meta="compound">
            <ld:field name="fps" ld:level="3" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
            <ld:field ld:anon-compound="true" ld:level="3" ld:meta="compound">
              <ld:field name="x" ld:level="3" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
              <ld:field name="y" ld:level="3" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
            </ld:field>
          </ld:field>
        </ld:data-definition>
        """        
        root = ET.fromstring(XML)
        out = self.sut.render(root[0])
        self.assertStructEqual(out, """
        message T_anon {
          int32 x = 1;
          int32 y = 2;
        }
        oneof anon {
          int32 fps = 1;
          T_anon anon = 2;
        }
        """)
