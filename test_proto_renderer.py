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
          optional int32 unk_54_ref = 1;
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
    # test fields and local types
    #

    def test_render_field_local_enum(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:subtype="enum" base-type="int32_t" name="state" ld:level="1" ld:meta="compound" ld:typedef-name="T_state">
            <enum-item name="started"/>
            <enum-item name="active"/>
          </ld:field>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_field(root[0])
        self.assertEqual(len(self.sut.imports), 0)
        self.assertStructEqual(out, """
        enum T_state {
          state_started = 0;
          state_active = 1;
        }
        required T_state state = 1;
        """)

    def test_render_field_global_enum(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:subtype="enum" name="type" base-type="int32_t" type-name="talk_choice_type" ld:level="1" ld:meta="global"/>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_field(root[0])
        self.assertListEqual(list(self.sut.imports), ['talk_choice_type'])
        self.assertStructEqual(out, """
        required talk_choice_type type = 1;
        """)
    
    def test_render_field_container(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:meta="container" ld:level="1" ld:subtype="stl-vector" type-name="int16_t" name="talk_choices" ld:is-container="true">
            <ld:item ld:level="2" ld:meta="number" ld:subtype="int16_t" ld:bits="16"/>
        </ld:field>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_field(root[0])
        self.assertEqual(len(self.sut.imports), 0)
        self.assertStructEqual(out, """
        repeated int32 talk_choices = 1;
        """)

    @unittest.skip('FIXME')
    def test_render_field_container_of_container(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:meta="container" ld:level="3" ld:subtype="stl-vector" name="region_masks" ld:is-container="true">
          <ld:item ld:level="4" ld:meta="pointer" ld:is-container="true">
            <ld:item ld:level="5" ld:meta="static-array" count="16" ld:is-container="true">
              <ld:item ld:level="6" ld:meta="static-array" count="16" type-name="uint8_t" comment="1 bit per entity" ld:is-container="true"><ld:item ld:level="7" ld:meta="number" ld:subtype="uint8_t" ld:unsigned="true" ld:bits="8"/></ld:item>
            </ld:item>
          </ld:item>
        </ld:field>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_field(root[0])
        self.assertEqual(len(self.sut.imports), 0)
        self.assertStructEqual(out, """
        message T_region_masks {
          message T_region_masks_inner {
            repeated uint32 value = 1;
          }
          repeated T_region_masks_inner value = 1;
        }
        repeated T_region_masks region_masks = 1;
        """)
    
    def test_render_field_container_pointer_to_primitive(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:meta="container" ld:level="1" ld:subtype="stl-vector" name="name_singular" pointer-type="stl-string" ld:is-container="true">
          <ld:item ld:meta="pointer" ld:is-container="true" ld:level="2" type-name="stl-string">
            <ld:item ld:level="3" ld:meta="primitive" ld:subtype="stl-string"/>
          </ld:item>
        </ld:field>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_field(root[0])
        self.assertEqual(len(self.sut.imports), 0)
        self.assertStructEqual(out, """
        repeated string name_singular = 1;
        """)
    
    def test_render_field_container_pointer_to_global(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:meta="container" ld:level="1" ld:subtype="stl-vector" name="children" pointer-type="building" ld:is-container="true">
          <ld:item ld:meta="pointer" ld:is-container="true" ld:level="2" type-name="building">
            <ld:item ld:level="3" ld:meta="global" type-name="building"/>
          </ld:item>
        </ld:field>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_field(root[0])
        self.assertEqual(len(self.sut.imports), 0)
        self.assertStructEqual(out, """
        optional int32 children_ref = 1;
        """)
    
    def test_render_field_pointer_to_anon_compound(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:level="1" ld:meta="pointer" name="map" is-array="true" ld:is-container="true">
          <ld:item ld:level="2" ld:meta="pointer" is-array="true" ld:is-container="true">
            <ld:item ld:meta="compound" ld:level="2">
              <ld:field ld:meta="container" ld:level="3" ld:subtype="stl-vector" name="entities" type-name="int32_t" ref-target="historical_entity" ld:is-container="true">
                <ld:item ref-target="historical_entity" ld:level="4" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
              </ld:field>
            </ld:item>
          </ld:item>
        </ld:field>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_field(root[0])
        self.assertListEqual(list(self.sut.imports), [])
        self.assertStructEqual(out, """
        message T_map {
          repeated int32 entities = 1;
        }
        required T_map map = 1;
        """)
            
    def test_render_field_pointer_to_container(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:level="1" ld:meta="pointer" name="temporary_trait_changes" comment="sum of inebriation or so personality changing effects" ld:is-container="true">
          <ld:item ld:level="2" ld:meta="static-array" type-name="int16_t" name="traits" count="50" index-enum="personality_facet_type" ld:is-container="true">
            <ld:item ld:level="3" ld:meta="number" ld:subtype="int16_t" ld:bits="16"/>
          </ld:item>
        </ld:field>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_field(root[0])
        self.assertListEqual(list(self.sut.imports), [])
        self.assertStructEqual(out, """
        repeated int32 temporary_trait_changes = 1;
        """)

    def test_render_field_bitfield(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:subtype="bitfield" name="flags_0" type-name="knowledge_scholar_flags_0" ld:level="2" ld:meta="global"/>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_field(root[0])
        self.assertEqual(list(self.sut.imports), ['knowledge_scholar_flags_0'])
        self.assertStructEqual(out, """
        required knowledge_scholar_flags_0 flags_0 = 1;
        """)

    def test_render_field_local_compound(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field name="unk" ld:level="1" ld:meta="compound" ld:typedef-name="T_unk">
            <ld:field ld:level="2" ld:meta="pointer" name="event" type-name="entity_event" ld:is-container="true">
              <ld:item ld:level="3" ld:meta="global" type-name="entity_event"/>
            </ld:field>
            <ld:field ld:level="2" ld:meta="number" ld:subtype="int32_t" ld:bits="32" ld:anon-name="anon_2"/>
          </ld:field>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_field(root[0])
        self.assertEqual(len(self.sut.imports), 0)
        self.assertStructEqual(out, """
        message T_unk {
          optional int32 event_ref = 1;
          required int32 anon_2 = 2;
        }
        required T_unk unk = 1;
        """)

    def test_render_field_anon_compound(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:anon-compound="true" ld:level="1" ld:meta="compound">
            <ld:field name="x" ld:level="2" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
            <ld:field ld:subtype="enum" base-type="int16_t" name="item_type" type-name="item_type" ld:level="2" ld:meta="global"/>
          </ld:field>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_field(root[0])
        self.assertEqual(list(self.sut.imports), ['item_type'])
        self.assertStructEqual(out, """
        message T_anon {
          required int32 x = 1;
          required item_type item_type = 2;
        }
        """)

    def test_render_field_compound_union(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field name="data" is-union="true" init-value="-1" ld:level="1" ld:meta="compound" ld:typedef-name="T_data" ld:in-union="true">
            <ld:field name="glorify_hf" ref-target="historical_figure" ld:level="2" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
            <ld:field name="artifact_is_heirloom_of_family_hfid" ref-target="historical_figure" ld:level="2" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>"historical_entity" ld:level="2" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
          </ld:field>
        </ld:data-definition>
        """        
        root = etree.fromstring(XML)
        out = self.sut.render_field(root[0])
        self.assertEqual(len(self.sut.imports), 0)
        self.assertStructEqual(out, """
        oneof data {
          int32 glorify_hf = 1;
          int32 artifact_is_heirloom_of_family_hfid = 2;
        }
        """)

    def test_render_field_anon_compound_union(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:anon-compound="true" is-union="true" ld:level="3" ld:meta="compound">
            <ld:field name="fps" ld:level="3" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
            <ld:field ld:anon-compound="true" ld:level="3" ld:meta="compound">
              <ld:field name="x" ld:level="3" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
              <ld:field name="y" ld:level="3" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
            </ld:field>
            <ld:field ld:subtype="enum" base-type="int16_t" name="item_type" type-name="item_type" ld:level="3" ld:meta="global"/>
          </ld:field>
        </ld:data-definition>
        """        
        root = etree.fromstring(XML)
        out = self.sut.render_field(root[0])
        self.assertEqual(list(self.sut.imports), ['item_type'])
        self.assertStructEqual(out, """
        message T_anon_2 {
          required int32 x = 1;
          required int32 y = 2;
        }
        oneof anon {
          int32 fps = 1;
          T_anon_2 anon_2 = 2;
          item_type item_type = 3;
        }
        """)

    def test_render_field_anon_bitfield(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:subtype="bitfield" since="v0.42.01" ld:level="1" ld:meta="compound" ld:anon-name="anon_3" ld:typedef-name="T_anon_3">
          <ld:field name="petition_not_accepted" comment="this gets unset by accepting a petition" ld:level="2" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
          <ld:field name="convicted_accepted" comment="convicted for PositionCorruption/accepted for Location" ld:level="2" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
        </ld:field>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_field(root[0])
        self.assertEqual(len(self.sut.imports), 0)
        self.assertStructEqual(out, """
        message T_anon_3 {
          enum mask {
            petition_not_accepted = 0x0; /* this gets unset by accepting a petition */
            convicted_accepted = 0x1; /* convicted for PositionCorruption/accepted for Location */
          }
          required fixed32 flags = 1;
        }
        required T_anon_3 anon_3 = 1;
        """)

    def test_render_field_bitfield(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:subtype="bitfield" name="gems_use" ld:level="1" ld:meta="compound">
          <ld:field name="noun" ld:level="2" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
          <ld:field name="adj" ld:level="2" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
          <ld:field name="adj_noun" ld:level="2" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
        </ld:field>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_field(root[0])
        self.assertEqual(len(self.sut.imports), 0)
        self.assertStructEqual(out, """
        message T_gems_use {
          enum mask {
            noun = 0x0;
            adj = 0x1;
            adj_noun = 0x2;
          }
          required fixed32 flags = 1;
        }
        required T_gems_use gems_use = 1;
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
