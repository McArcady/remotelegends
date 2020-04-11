#!/bin/python3

import unittest
import mock
import re
import subprocess
from lxml import etree

from renderer import Renderer

OUTPUT_FNAME = 'output.proto'

class TestRender(unittest.TestCase):

    output = ''

    @classmethod
    def setUpClass(cls):
        with open(OUTPUT_FNAME, 'w') as fil:
            fil.write('syntax = "proto3";\n')
            
    def setUp(self):
        self.sut = Renderer('ns')

    def tearDown(self):
        with open(OUTPUT_FNAME, 'a') as fil:
            fil.write(self.output)

    @classmethod
    def tearDownClass(cls):
        subprocess.check_call(['protoc -I. -o%s.pb  %s' % (OUTPUT_FNAME, OUTPUT_FNAME)], shell=True)

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
        root = etree.fromstring(XML)
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
        root = etree.fromstring(XML)
        out = self.sut.render(root[0])
        self.assertStructEqual(out, """
        enum T_state {
          started = 0;
          active = 1;
        }
        T_state state = 1;
        """)

    def test_render_global_enum(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:subtype="enum" name="type" base-type="int32_t" type-name="talk_choice_type" ld:level="1" ld:meta="global"/>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render(root[0])
        self.assertListEqual(self.sut.imports, ['talk_choice_type'])
        self.assertStructEqual(out, """
        talk_choice_type type = 1;
        """)
    
    def test_render_container(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:meta="container" ld:level="1" ld:subtype="stl-vector" type-name="int16_t" name="talk_choices" ld:is-container="true"><ld:item ld:level="2" ld:meta="number" ld:subtype="int16_t" ld:bits="16"/></ld:field>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render(root[0])
        self.assertStructEqual(out, """
        repeated int32 talk_choices = 1;
        """)
        
    def test_render_struct_type_with_primitive_fields(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="struct-type" ld:level="0" type-name="conversation1">
          <ld:field name="conv_title" ld:level="1" ld:meta="primitive" ld:subtype="stl-string"/>
          <ld:field name="unk_30" ref-target="unit" ld:level="1" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
        </ld:global-type>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render(root[0])
        self.assertStructEqual(out, """
        message conversation1 {
          string conv_title = 1;
          int32 unk_30 = 2;
        }
        """)
        self.output += out + '\n'

    def test_render_struct_type_with_complex_fields(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="struct-type" ld:level="0" type-name="conversation2">
          <ld:field name="conv_title" ld:level="1" ld:meta="primitive" ld:subtype="stl-string"/>
          <ld:field ld:subtype="enum" base-type="int32_t" name="state" ld:level="1" ld:meta="compound" ld:typedef-name="T_state">
            <enum-item name="started"/>
            <enum-item name="active"/>
          </ld:field>
          <ld:field ld:meta="container" ld:level="1" ld:subtype="stl-vector" type-name="int16_t" name="talk_choices" ld:is-container="true">
            <ld:item ld:level="2" ld:meta="number" ld:subtype="int16_t" ld:bits="16"/>
          </ld:field>
        </ld:global-type>
        </ld:data-definition>   
        """
        root = etree.fromstring(XML)
        out = self.sut.render(root[0])
        self.assertStructEqual(out, """
        message conversation2 {
          string conv_title = 1;
          enum T_state {
            started = 0;
            active = 1;
          }
          T_state state = 2;
          repeated int32 talk_choices = 3;
        }
        """)
        self.output += out + '\n'

    def test_render_struct_type_with_pointer(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="struct-type" ld:level="0" type-name="conversation3">
          <ld:field ld:meta="container" ld:level="1" ld:subtype="stl-vector" name="unk_54" pointer-type="nemesis_record" ld:is-container="true">
            <ld:item ld:meta="pointer" ld:is-container="true" ld:level="2" type-name="nemesis_record">
              <ld:item ld:level="3" ld:meta="global" type-name="nemesis_record"/>
          </ld:item></ld:field>
        </ld:global-type>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render(root[0])
        self.assertListEqual(self.sut.imports, ['nemesis_record'])
        self.assertStructEqual(out, """
        message conversation3 {
          repeated nemesis_record unk_54 = 1;
        }
        """)

    def test_render_compound(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field name="unk" ld:level="1" ld:meta="compound" ld:typedef-name="T_unk">
            <ld:field ld:level="2" ld:meta="pointer" name="event" type-name="entity_event" ld:is-container="true"><ld:item ld:level="3" ld:meta="global" type-name="entity_event"/></ld:field>
            <ld:field ld:level="2" ld:meta="number" ld:subtype="int32_t" ld:bits="32" ld:anon-name="anon_2"/>
          </ld:field>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render(root[0])
        self.assertStructEqual(out, """
        message T_unk {
          entity_event event = 1;
          int32 anon_2 = 2;
        }
        T_unk unk = 1;
        """)

    def test_render_anon_compound(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:anon-compound="true" ld:level="3" ld:meta="compound">
            <ld:field name="x" ld:level="3" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
            <ld:field name="y" ld:level="3" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
          </ld:field>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render(root[0])
        self.assertStructEqual(out, """
        message T_anon {
          int32 x = 1;
          int32 y = 2;
        }
        """)
        self.output += out + '\n'

    def test_render_compound_union(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field name="data" is-union="true" init-value="-1" ld:level="1" ld:meta="compound" ld:typedef-name="T_data" ld:in-union="true">
            <ld:field name="glorify_hf" ref-target="historical_figure" ld:level="2" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
            <ld:field name="artifact_is_heirloom_of_family_hfid" ref-target="historical_figure" ld:level="2" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>"historical_entity" ld:level="2" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
          </ld:field>
        </ld:data-definition>
        """        
        root = etree.fromstring(XML)
        out = self.sut.render(root[0])
        self.assertStructEqual(out, """
        oneof data {
          int32 glorify_hf = 1;
          int32 artifact_is_heirloom_of_family_hfid = 2;
        }
        """)

    def test_render_anon_compound_union(self):
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
        root = etree.fromstring(XML)
        out = self.sut.render(root[0])
        self.assertStructEqual(out, """
        message T_anon {
          int32 x = 1;
          int32 y = 2;
        }
        oneof anon {
          int32 fps = 1;
          T_anon anon_2 = 2;
        }
        """)

    def test_render_bitfield_type(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="bitfield-type" ld:level="0" type-name="announcement_flags">
          <ld:field name="DO_MEGA" comment="BOX" ld:level="1" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
          <ld:field name="PAUSE" comment="P" ld:level="1" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
          <ld:field name="RECENTER" comment="R" ld:level="1" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
        </ld:global-type>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render(root[0])
        self.assertStructEqual(out, """
        message announcement_flags {
          enum mask {
            DO_MEGA = 0; /* BOX */
            PAUSE = 1; /* P */
            RECENTER = 2; /* R */
          }
          fixed32 flags = 1;
        }
        """)

    def test_render_bitfield(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:subtype="bitfield" since="v0.42.01" ld:level="1" ld:meta="compound" ld:anon-name="anon_3" ld:typedef-name="T_anon_3">
          <ld:field name="petition_not_accepted" comment="this gets unset by accepting a petition" ld:level="2" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
          <ld:field name="convicted_accepted" comment="convicted for PositionCorruption/accepted for Location" ld:level="2" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
        </ld:field>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render(root[0])
        self.assertStructEqual(out, """
        message T_anon_3 {
          enum mask {
            petition_not_accepted = 0; /* this gets unset by accepting a petition */
            convicted_accepted = 1; /* convicted for PositionCorruption/accepted for Location */
          }
          fixed32 flags = 1;
        }
        T_anon_3 anon_3 = 1;
        """)


    def _test_render_global_type(self):
        tree = etree.parse('codegen/codegen.out.xml')
        root = tree.getroot()
        ns = re.match(r'{.*}', root.tag).group(0)
        sut = Renderer(ns)
        
        for e in root:
            print( 'line '+str(e.sourceline)+':', e.get(f'{ns}meta'), e.get(f'type-name') )
            out = sut.render(e)
            self.output += out + '\n'
