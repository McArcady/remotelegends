#!/bin/python3

import os
import unittest
import subprocess
from lxml import etree

from cpp_renderer import CppRenderer
from proto_renderer import ProtoRenderer

OUTPUT_FNAME = 'output.proto'


class TestRenderType(unittest.TestCase):

    output = ''

    @classmethod
    def setUpClass(cls):
        with open(OUTPUT_FNAME, 'w') as fil:
            fil.write('syntax = "proto2";\n')
    
    def setUp(self):
        self.sut_proto = ProtoRenderer('ns')
        self.sut_cpp = CppRenderer('ns', 'dfproto', 'DFProto')
        self.maxDiff = None

    def tearDown(self):
        with open(OUTPUT_FNAME, 'a') as fil:
            fil.write(self.output)

    @classmethod
    def tearDownClass(cls):
#        subprocess.check_call(['protoc -I. -o%s.pb  %s' % (OUTPUT_FNAME, OUTPUT_FNAME)], shell=True)
#        os.remove(OUTPUT_FNAME+'.pb')
        os.remove(OUTPUT_FNAME)

    def assertStructEqual(self, str1, str2):
        self.assertEqual(''.join(str1.split()), ''.join(str2.split()), str1+'/'+str2)

    def check_rendering(self, XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS):
        xml = etree.fromstring(XML)[0]
        out = self.sut_proto.render_type(xml)
        self.assertStructEqual(out, PROTO)
        self.assertEqual(sorted(list(self.sut_proto.imports)), sorted(IMPORTS))
        self.output += out
        if CPP:
            out = self.sut_cpp.render_type(xml)
            self.assertStructEqual(out, CPP)
            self.assertEqual(sorted(list(self.sut_cpp.dfproto_imports)), sorted(DFPROTO_IMPORTS))


    #
    # enum
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
        PROTO = """
        enum ui_advmode_menu {
          ui_advmode_menu_Default = 0;
          ui_advmode_menu_Look = 1;
        }
        """
        CPP = None
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)
    
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
        PROTO = """
        enum conflict_level {
          conflict_level_Encounter = 0;
          conflict_level_Horseplay = 1;
          conflict_level_None = -1;
          conflict_level_anon_m3 = -3;
        }
        """
        CPP = None
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    
    #
    # bitfield
    #

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
        PROTO = """
        message announcement_flags {
          enum mask {
            DO_MEGA = 0x0; /* BOX */
            PAUSE = 0x1; /* P */
            RECENTER = 0x2; /* R */
          }
          required fixed32 flags = 1;
        }
        """
        CPP = """
        void DFProto::describe_announcement_flags(dfproto::announcement_flags* proto, df::announcement_flags* dfhack)
        {
          proto->set_flags(dfhack->whole);
        }
        """


    #
    # df-linked-list
    #
    
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
        PROTO = """
        message job_list_link {
          optional int32 next_ref = 1;
        }
        """
        CPP = """
        void DFProto::describe_job_list_link(dfproto::job_list_link* proto, df::job_list_link* dfhack) {
          proto->set_next_ref(dfhack->next->id);
        }
        """
        IMPORTS = []
        DFPROTO_IMPORTS = ['job_list_link']
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)
        

    #
    # struct/class
    #
    
    def test_render_global_type_struct_with_primitive_fields(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="struct-type" ld:level="0" type-name="conversation1">
          <ld:field name="conv_title" ld:level="1" ld:meta="primitive" ld:subtype="stl-string"/>
          <ld:field name="unk_30" ref-target="unit" ld:level="1" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
        </ld:global-type>
        </ld:data-definition>
        """
        PROTO = """
        message conversation1 {
          required string conv_title = 1;
          required int32 unk_30 = 2;
        }
        """
        CPP = """
        void DFProto::describe_conversation1(dfproto::conversation1* proto, df::conversation1* dfhack) {
          proto->set_conv_title(dfhack->conv_title);
          proto->set_unk_30(dfhack->unk_30);
        }
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    def test_render_global_type_struct(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="struct-type" ld:level="0" type-name="campfire">
          <ld:field type-name="coord" name="pos" ld:level="1" ld:meta="global"/>
          <ld:field name="timer" ld:level="1" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
        </ld:global-type>
        </ld:data-definition>
        """
        PROTO = """
        message campfire {
          required coord pos = 1;
          required int32 timer = 2;
        }
        """
        CPP = """
        void DFProto::describe_campfire(dfproto::campfire* proto, df::campfire* dfhack)
        {
	  describe_coord(proto->mutable_pos(), &dfhack->pos);
	  proto->set_timer(dfhack->timer);
        }
        """
        IMPORTS = ['coord']
        DFPROTO_IMPORTS = ['coord']
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    def test_render_global_type_struct_with_enum_and_union(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="struct-type" ld:level="0" type-name="history_event_reason_info">
          <ld:field ld:subtype="enum" name="type" type-name="history_event_reason" base-type="int32_t" ld:level="1" ld:meta="global"/>
          <ld:field name="data" is-union="true" init-value="-1" ld:level="1" ld:meta="compound" ld:typedef-name="T_data" ld:in-union="true">
            <ld:field name="glorify_hf" ref-target="historical_figure" ld:level="2" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
            <ld:field name="artifact_is_heirloom_of_family_hfid" ref-target="historical_figure" ld:level="2" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>"historical_entity" ld:level="2" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
          </ld:field>
        </ld:global-type>
        </ld:data-definition>
        """
        PROTO = """
        message history_event_reason_info {
          required history_event_reason type = 1;
          oneof data {
            int32 glorify_hf = 2;
            int32 artifact_is_heirloom_of_family_hfid = 3;
          }
        }
        """
        CPP = """
        void DFProto::describe_history_event_reason_info(dfproto::history_event_reason_info* proto, df::history_event_reason_info* dfhack) {
          proto->set_type(static_cast<dfproto::history_event_reason>(dfhack->type));
          switch (dfhack->type) {
            case ::df::enums::history_event_reason::glorify_hf:
              proto->set_glorify_hf(dfhack->data.glorify_hf);
              break;
            case ::df::enums::history_event_reason::artifact_is_heirloom_of_family_hfid:
              proto->set_artifact_is_heirloom_of_family_hfid(dfhack->data.artifact_is_heirloom_of_family_hfid);
              break;
            default:
              proto->clear_data();           
          }
        }
        """
        IMPORTS = ['history_event_reason']
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

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
        PROTO = """
        message projectile {
          optional int32 link_ref = 1;
        }
        """
        CPP = """
        void DFProto::describe_projectile(dfproto::projectile* proto, df::projectile* dfhack) {
          proto->set_link_ref(dfhack->link->id);
        }
        """
        IMPORTS = []
        DFPROTO_IMPORTS = ['proj_list_link']
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    def test_render_global_type_struct_with_container_of_pointers(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="struct-type" ld:level="0" type-name="conversation">
          <ld:field ld:meta="container" ld:level="1" ld:subtype="stl-vector" name="unk_54" pointer-type="nemesis_record" ld:is-container="true">
            <ld:item ld:meta="pointer" ld:is-container="true" ld:level="2" type-name="nemesis_record">
              <ld:item ld:level="3" ld:meta="global" type-name="nemesis_record"/>
          </ld:item></ld:field>
        </ld:global-type>
        </ld:data-definition>
        """
        PROTO = """
        message conversation {
          repeated int32 unk_54_ref = 1;
        }
        """
        CPP = """
        void DFProto::describe_conversation(dfproto::conversation* proto, df::conversation* dfhack) {
	  for (size_t i=0; i<dfhack->unk_54.size(); i++) {
	    proto->add_unk_54_ref(dfhack->unk_54[i]->id);
	  }
        }
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    def test_render_global_type_struct_with_inheritance(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="class-type" ld:level="0" type-name="adventure_item" inherits-from="adventure_item_interact_choicest">
          <ld:field ld:level="1" ld:meta="pointer" type-name="item" ld:is-container="true">
            <ld:item ld:level="2" ld:meta="global" type-name="item"/>
          </ld:field>
        </ld:global-type>
        </ld:data-definition>
        """
        PROTO = """
        message adventure_item {
          required adventure_item_interact_choicest parent = 1; /* parent type */
          optional int32 anon_2_ref = 2;
        }
        """
        CPP = """
        void DFProto::describe_adventure_item(dfproto::adventure_item* proto, df::adventure_item* dfhack) {
	  describe_adventure_item_interact_choicest(proto->mutable_parent(), dfhack);
	  proto->set_anon_2_ref(dfhack->anon_2->id);
        }
        """
        IMPORTS = ['adventure_item_interact_choicest']
        DFPROTO_IMPORTS = ['adventure_item_interact_choicest', 'item']
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)
        
    def test_render_global_type_with_anon_compound(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="struct-type" ld:level="0" type-name="entity_claim_mask">
        <ld:field ld:level="1" ld:meta="pointer" name="map" is-array="true" ld:is-container="true">
          <ld:item ld:level="2" ld:meta="pointer" is-array="true" ld:is-container="true">
            <ld:item ld:meta="compound" ld:level="2">
              <ld:field ld:meta="container" ld:level="3" ld:subtype="stl-vector" name="entities" type-name="int32_t" ref-target="historical_entity" ld:is-container="true">
                <ld:item ref-target="historical_entity" ld:level="4" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
              </ld:field>
            </ld:item>
          </ld:item>
        </ld:field>
        </ld:global-type>
        </ld:data-definition>
        """
        PROTO =  """
        message entity_claim_mask {
          message T_map {
            repeated int32 entities = 1;
          }
          optional T_map map = 1;
        }
        """
        CPP = """
        void DFProto::describe_entity_claim_mask(dfproto::entity_claim_mask* proto, df::entity_claim_mask* dfhack) {
          auto describe_T_map = [](dfproto::entity_claim_mask_T_map* proto, df::entity_claim_mask::T_map* dfhack) {
  	    for (size_t i=0; i<dfhack->entities.size(); i++) {
	      proto->add_entities(dfhack->entities[i]);
	    }
          };
          describe_T_map(proto->mutable_map(), &dfhack->map);
        }
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)
    
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
        PROTO = """
        /* comment */
        message adventure_movement_optionst {
          required coord dest = 1;
          required coord source = 2;
        }
        """
        CPP = """
        /* comment */
        void DFProto::describe_adventure_movement_optionst(dfproto::adventure_movement_optionst* proto, df::adventure_movement_optionst* dfhack) {
          describe_coord(proto->mutable_dest(), &dfhack->dest);
          describe_coord(proto->mutable_source(), &dfhack->source);
        }
        """
        IMPORTS = ['coord']
        DFPROTO_IMPORTS = ['coord']
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)
