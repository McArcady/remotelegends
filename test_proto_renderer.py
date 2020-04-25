#!/bin/python3

import os
import unittest
import mock
import re
import subprocess
from lxml import etree

from proto_renderer import ProtoRenderer

OUTPUT_FNAME = 'output.proto'

class TestProtoRenderer(unittest.TestCase):

    output = ''

    @classmethod
    def setUpClass(cls):
        with open(OUTPUT_FNAME, 'w') as fil:
            fil.write('syntax = "proto2";\n')
            
    def setUp(self):
        self.sut = ProtoRenderer('ns')

    def tearDown(self):
        with open(OUTPUT_FNAME, 'a') as fil:
            fil.write(self.output)

    @classmethod
    def tearDownClass(cls):
        subprocess.check_call(['protoc -I. -o%s.pb  %s' % (OUTPUT_FNAME, OUTPUT_FNAME)], shell=True)
        os.remove(OUTPUT_FNAME)
        os.remove(OUTPUT_FNAME+'.pb')

    def assertStructEqual(self, str1, str2):
        self.assertEqual(''.join(str1.split()), ''.join(str2.split()), str1+'/'+str2)

    
    #
    # test global types
    #
    
    def test_render_global_type_enum(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:global-type ld:meta="enum-type" ld:level="0" type-name="ui_advmode_menu" base-type="int16_t">
            <enum-item name="Default" value="0"/>
            <enum-item name="Look"/>
          </ld:global-type>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_type(root[0])
        self.assertEqual(len(self.sut.imports), 0)
        self.assertStructEqual(out, """
        enum ui_advmode_menu {
          ui_advmode_menu_Default = 0;
          ui_advmode_menu_Look = 1;
        }
        """)
        self.output += out + '\n'
    
    def test_render_global_type_enum_with_values(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="enum-type" ld:level="0" type-name="conflict_level">
          <enum-item name="None" value="-1"/>
          <enum-item name="Encounter"/>
          <enum-item name="Horseplay"/>
          <enum-item value="-3"/>
        </ld:global-type>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_type(root[0])
        self.assertEqual(len(self.sut.imports), 0)
        self.assertStructEqual(out, """
        enum conflict_level {
          conflict_level_Encounter = 0;
          conflict_level_Horseplay = 1;
          conflict_level_None = -1;
          conflict_level_anon_m3 = -3;
        }
        """)
        self.output += out + '\n'

    
    def test_render_global_type_struct_with_primitive_fields(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="struct-type" ld:level="0" type-name="conversation1">
          <ld:field name="conv_title" ld:level="1" ld:meta="primitive" ld:subtype="stl-string"/>
          <ld:field name="unk_30" ref-target="unit" ld:level="1" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
        </ld:global-type>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_type(root[0])
        self.assertEqual(len(self.sut.imports), 0)
        self.assertStructEqual(out, """
        message conversation1 {
          required string conv_title = 1;
          required int32 unk_30 = 2;
        }
        """)
        self.output += out + '\n'
    
    def test_render_global_type_struct_with_recursive_ref(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="struct-type" ld:subtype="df-linked-list-type" ld:level="0" type-name="job_list_link" item-type="job">
          <ld:field name="next" type-name="job_list_link" ld:level="1" ld:meta="pointer" ld:is-container="true">
            <ld:item ld:level="2" ld:meta="global" type-name="job_list_link"/>
</ld:field>
        </ld:global-type>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_type(root[0])
        # avoid recursive import
        self.assertEqual(len(self.sut.imports), 0)
        self.assertStructEqual(out, """
        message job_list_link {
          optional int32 next_ref = 1;
        }
        """)
        self.output += out + '\n'

    def test_render_global_type_struct_with_list_link(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="class-type" ld:level="0" type-name="projectile" original-name="projst" df-list-link-type="proj_list_link" df-list-link-field="link" key-field="id">
          <ld:field ld:level="1" ld:meta="pointer" name="link" type-name="proj_list_link" ld:is-container="true">
            <ld:item ld:level="2" ld:meta="global" type-name="proj_list_link"/>
        </ld:field>
        </ld:global-type>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_type(root[0])
        # avoid recursive import
        self.assertEqual(len(self.sut.imports), 0)
        self.assertStructEqual(out, """
        message projectile {
          optional int32 link_ref = 1;
        }
        """)
        self.output += out + '\n'

    def test_render_global_type_struct_with_complex_fields(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="struct-type" ld:level="0" type-name="conversation2">
          <ld:field name="conv_title" ld:level="1" ld:meta="primitive" ld:subtype="stl-string"/>
          <ld:field ld:subtype="enum" base-type="int32_t" name="state" ld:level="1" ld:meta="compound" ld:typedef-name="T_state">
            <enum-item name="started"/>
            <enum-item name="active"/>
          </ld:field>
          <ld:field ld:anon-compound="true" is-union="true" ld:level="1" ld:meta="compound">
            <ld:field name="creature_id" ref-target="creature_raw" ld:level="1" ld:meta="number" ld:subtype="int16_t" ld:bits="16"/>
            <ld:field name="color_id" ref-target="descriptor_color" ld:level="1" ld:meta="number" ld:subtype="int16_t" ld:bits="16"/>
          </ld:field>
          <ld:field ld:meta="container" ld:level="1" ld:subtype="stl-vector" type-name="int16_t" name="talk_choices" ld:is-container="true">
            <ld:item ld:level="2" ld:meta="number" ld:subtype="int16_t" ld:bits="16"/>
          </ld:field>
        </ld:global-type>
        </ld:data-definition>   
        """
        root = etree.fromstring(XML)
        out = self.sut.render_type(root[0])
        self.assertEqual(len(self.sut.imports), 0)
        self.assertStructEqual(out, """
        message conversation2 {
          required string conv_title = 1;
          enum T_state {
            state_started = 0;
            state_active = 1;
          }
          required T_state state = 2;
          oneof anon {
            int32 creature_id = 3;
            int32 color_id = 4;
          }
          repeated int32 talk_choices = 5;
        }
        """)
        self.output += out + '\n'

    def test_render_global_type_struct_with_container_of_pointers(self):
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
        out = self.sut.render_type(root[0])
        self.assertListEqual(list(self.sut.imports), [])
        self.assertStructEqual(out, """
        message conversation3 {
          repeated int32 unk_54_ref = 1;
        }
        """)
        self.output += out + '\n'

    def test_render_global_type_struct_with_inheritance(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="class-type" ld:level="0" type-name="adventure_item" inherits-from="adventure_item_interact_choicest">
          <ld:field ld:level="1" ld:meta="pointer" type-name="item" ld:is-container="true"><ld:item ld:level="2" ld:meta="global" type-name="item"/></ld:field>
        </ld:global-type>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_type(root[0])
        self.assertListEqual(list(self.sut.imports), ['adventure_item_interact_choicest'])
        self.assertStructEqual(out, """
        message adventure_item {
          required adventure_item_interact_choicest parent = 1; /* parent type */
          optional int32 anon_2_ref = 2;
        }
        """)

    def test_render_global_type_class(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="class-type" ld:level="0" type-name="adventure_movement_optionst" comment="comment">
          <ld:field name="dest" type-name="coord" ld:level="1" ld:meta="global"/>
          <ld:field name="source" type-name="coord" ld:level="1" ld:meta="global"/>
          <virtual-methods>
            <vmethod ld:level="1"><ld:field ld:level="2" ld:meta="pointer" ld:is-container="true"/></vmethod>
            <vmethod ld:level="1"/>
          </virtual-methods>
        </ld:global-type>
        </ld:data-definition>   
        """
        root = etree.fromstring(XML)
        out = self.sut.render_type(root[0])
        self.assertListEqual(list(self.sut.imports), ['coord'])
        self.assertStructEqual(out, """
        /* comment */
        message adventure_movement_optionst {
          required coord dest = 1;
          required coord source = 2;
        }
        """)

    def test_render_global_type_bitfield(self):
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
        out = self.sut.render_type(root[0])
        self.assertEqual(len(self.sut.imports), 0)
        self.assertStructEqual(out, """
        message announcement_flags {
          enum mask {
            DO_MEGA = 0x0; /* BOX */
            PAUSE = 0x1; /* P */
            RECENTER = 0x2; /* R */
          }
          required fixed32 flags = 1;
        }
        """)
        self.output += out + '\n'


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
        message entity_position_raw {
          required int32 squad_sz = 1;
        }
        """)
    

    def _test_render_global_types(self):
        tree = etree.parse('codegen/codegen.out.xml')
        root = tree.getroot()
        ns = re.match(r'{.*}', root.tag).group(0)
        sut = ProtoRenderer(ns)
        
        for e in root:
            print( 'line '+str(e.sourceline)+':', e.get(f'{ns}meta'), e.get(f'type-name') )
            out = sut.render_type(e)
            self.output += out + '\n'
