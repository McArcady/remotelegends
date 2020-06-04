#!/bin/python3

import unittest
from lxml import etree

from cpp_renderer import CppRenderer
from proto_renderer import ProtoRenderer

PROTO_FNAME = 'output.proto'
CPP_FNAME = 'output.cpp'


class TestRenderType(unittest.TestCase):

    proto_output = ''
    cpp_output = ''

    @classmethod
    def setUpClass(cls):
        with open(PROTO_FNAME, 'w') as fil:
            fil.write('syntax = "proto2";\n')
        with open(CPP_FNAME, 'w') as fil:
            fil.write('')
    
    def setUp(self):
        self.sut_proto = ProtoRenderer('ns')
        self.sut_cpp = CppRenderer('ns', 'dfproto', 'DFProto')
        self.maxDiff = None

    def tearDown(self):
        with open(PROTO_FNAME, 'a') as fil:
            fil.write(self.proto_output)
        with open(CPP_FNAME, 'a') as fil:
            fil.write(self.cpp_output)

    # @classmethod
    # def tearDownClass(cls):
    #     os.remove(PROTO_FNAME)
    #     os.remove(CPP_FNAME)

    def assertStructEqual(self, str1, str2):
        self.assertEqual(''.join(str1.split()), ''.join(str2.split()), str1+'/'+str2)

    def check_rendering(self, XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS):
        xml = etree.fromstring(XML)[0]
        out = self.sut_proto.render_type(xml)
        if len(PROTO):
            self.assertStructEqual(out, PROTO)
        self.assertEqual(sorted(list(self.sut_proto.imports)), sorted(IMPORTS))
        self.proto_output += out
        if CPP:
            out = self.sut_cpp.render_type(xml)
            self.assertStructEqual(out, CPP)
            self.assertEqual(sorted(list(self.sut_cpp.dfproto_imports)), sorted(DFPROTO_IMPORTS))
            self.cpp_output += out


    #
    # enum
    #
    
    def test_render_type_enum(self):
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
    
    def test_render_type_enum_with_values(self):
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
          conflict_level_anon_1 = -3;
        }
        """
        CPP = None
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    
    #
    # bitfield
    #

    def test_render_type_bitfield(self):
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
    # struct/class
    #
    
    def test_render_type_struct_with_primitive_fields(self):
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

    def test_render_type_struct(self):
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

    def test_render_type_struct_with_anon_fields(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="struct-type" ld:level="0" type-name="entity_site_link">
          <ld:field name="target" ref-target="world_site" comment="world.world_data.sites vector" ld:level="1" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
          <ld:field name="entity_id" ref-target="historical_entity" ld:level="1" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
          <ld:field ld:level="1" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
          <ld:field ld:level="1" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
        </ld:global-type>
        </ld:data-definition>
        """
        PROTO = """
        message entity_site_link {
          required int32 target = 1; /* world.world_data.sites vector */
          required int32 entity_id = 2;
          required int32 anon_1 = 3;
          required int32 anon_2 = 4;
        }
        """
        CPP = """
        void DFProto::describe_entity_site_link(dfproto::entity_site_link* proto, df::entity_site_link* dfhack) {
          proto->set_target(dfhack->target);
	  proto->set_entity_id(dfhack->entity_id);
          proto->set_anon_1(dfhack->anon_1);
	  proto->set_anon_2(dfhack->anon_2);
        }
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    def test_render_type_struct_with_local_bitfield_and_anon_flags(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="struct-type" ld:level="0" type-name="entity_site_link">
        <ld:field ld:level="1" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
        <ld:field ld:subtype="bitfield" name="flags" base-type="uint32_t" ld:level="1" ld:meta="compound">
          <ld:field name="residence" comment="site is residence" ld:level="2" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
          <ld:field ld:level="2" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
        </ld:field>  
        <ld:field ld:level="1" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
        </ld:global-type>
        </ld:data-definition>
        """
        PROTO = """
        message entity_site_link {
          required int32 anon_1 = 1;
          message T_flags {
            enum mask {
              residence = 0x0; /* site is residence */
              anon_1 = 0x1;
            }
            required fixed32 flags = 1;
          }
          required T_flags flags = 2;
          required int32 anon_2 = 3;
        }
        """
        CPP = """
        void DFProto::describe_entity_site_link(dfproto::entity_site_link* proto, df::entity_site_link* dfhack) {
          proto->set_anon_1(dfhack->anon_1);
          proto->mutable_flags()->set_flags(dfhack->flags.whole);
	  proto->set_anon_2(dfhack->anon_2);
        }
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    def test_render_type_struct_with_enum_and_union(self):
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

    def test_render_type_struct_with_container_of_pointers(self):
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
          repeated nemesis_record unk_54 = 1;
        }
        """
        CPP = """
        void DFProto::describe_conversation(dfproto::conversation* proto, df::conversation* dfhack) {
	  for (size_t i=0; i<dfhack->unk_54.size(); i++) {
	    describe_nemesis_record(proto->add_unk_54(), dfhack->unk_54[i]);
	  }
        }
        """
        IMPORTS = ['nemesis_record']
        DFPROTO_IMPORTS = ['nemesis_record']
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    def test_render_type_struct_with_inheritance(self):
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
          /* parent type */
          required adventure_item_interact_choicest parent = 1;
          optional item anon_1 = 2;
        }
        """
        CPP = """
        void DFProto::describe_adventure_item(dfproto::adventure_item* proto, df::adventure_item* dfhack) {
	  describe_adventure_item_interact_choicest(proto->mutable_parent(), dfhack);
	  describe_item(proto->mutable_anon_1(), dfhack->anon_1);
        }
        """
        IMPORTS = ['adventure_item_interact_choicest', 'item']
        DFPROTO_IMPORTS = ['adventure_item_interact_choicest', 'item']
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)
    
    def test_render_type_with_pointer_to_anon_compound(self):
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
          describe_T_map(proto->mutable_map(), dfhack->map);
        }
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    def test_render_type_with_recursive_compounds(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="struct-type" ld:level="0" type-name="historical_entity" key-field="id" instance-vector="$global.world.entities.all">
        <ld:field name="resources" ld:level="1" ld:meta="compound">
          <ld:field name="metal" ld:level="2" ld:meta="compound">
            <ld:field name="pick" type-name="material_vec_ref" ld:level="3" ld:meta="global"/>
            <ld:field name="weapon" type-name="material_vec_ref" ld:level="3" ld:meta="global"/>
          </ld:field>
        </ld:field>
        </ld:global-type>
        </ld:data-definition>
        """
        PROTO =  """
        message historical_entity {
          message T_resources {
            message T_metal {
              required material_vec_ref pick = 1;
              required material_vec_ref weapon = 2;
            }
            required T_metal metal = 1;
          }
          required T_resources resources = 1;
        }
        """
        CPP = """
        void DFProto::describe_historical_entity(dfproto::historical_entity* proto, df::historical_entity* dfhack) {
          auto describe_T_resources = [](dfproto::historical_entity_T_resources* proto, df::historical_entity::T_resources* dfhack) {
            auto describe_T_metal = [](dfproto::historical_entity_T_resources_T_metal* proto, df::historical_entity::T_resources::T_metal* dfhack) {
              describe_material_vec_ref(proto->mutable_pick(), &dfhack->pick);
              describe_material_vec_ref(proto->mutable_weapon(), &dfhack->weapon);
            };
            describe_T_metal(proto->mutable_metal(), &dfhack->metal);
          };
          describe_T_resources(proto->mutable_resources(), &dfhack->resources);
        }
        """
        IMPORTS = ['material_vec_ref']
        DFPROTO_IMPORTS = ['material_vec_ref']
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)
    
    def test_render_type_class(self):
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
        void DFProto::describe_adventure_movement_optionst(dfproto::adventure_movement_optionst* proto, df::adventure_movement_optionst* dfhack) {
          describe_coord(proto->mutable_dest(), &dfhack->dest);
          describe_coord(proto->mutable_source(), &dfhack->source);
        }
        """
        IMPORTS = ['coord']
        DFPROTO_IMPORTS = ['coord']
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)
    

    #
    # exceptions
    #
    
    def test_ignore_field(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="class-type" ld:level="0" type-name="general_ref" original-name="general_refst">
          <ld:field ld:meta="container" ld:level="1" ld:subtype="stl-vector" name="general_refs" pointer-type="general_ref" ld:is-container="true">
            <ld:item ld:meta="pointer" ld:is-container="true" ld:level="2" type-name="general_ref">
              <ld:item ld:level="3" ld:meta="global" type-name="general_ref"/>
            </ld:item>
          </ld:field>
        </ld:global-type>
        </ld:data-definition>
        """
        PROTO = """
        message general_ref {
          /* ignored field general_refs */
        }
        """
        CPP = """
        void DFProto::describe_general_ref(dfproto::general_ref* proto, df::general_ref* dfhack) {
        }
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        FILTER = 'ld:global-type[@type-name="general_ref"]/ld:field[@name="general_refs"]'
        self.sut_proto.add_exception_ignore(FILTER)
        self.sut_cpp.add_exception_ignore(FILTER)
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)
    
    def test_ignore_regex(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="class-type" ld:level="0" type-name="mytype">
          <ld:field name="unk_1" ld:level="1" ld:meta="number" ld:subtype="int16_t" ld:bits="16"/>
          <ld:field name="id" ld:level="1" ld:meta="number" ld:subtype="int16_t" ld:bits="16"/>
          <ld:field name="unk_2" ld:level="1" ld:meta="number" ld:subtype="int16_t" ld:bits="16"/>
        </ld:global-type>
        </ld:data-definition>
        """
        PROTO = """
        message mytype {
          /* ignored field unk_1 */
          required int32 id = 2;
          /* ignored field unk_2 */
        }
        """
        CPP = """
        void DFProto::describe_mytype(dfproto::mytype* proto, df::mytype* dfhack) {
          proto->set_id(dfhack->id);
        }
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        FILTER = "ld:global-type[@type-name='mytype']/ld:field[re:match(@name, 'unk_[0-9]+')]"
        self.sut_proto.add_exception_ignore(FILTER)
        self.sut_cpp.add_exception_ignore(FILTER)
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    def test_rename_field(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="struct-type" ld:level="0" type-name="entity_position_raw">
          <ld:field name="squad_size" ld:level="1" ld:meta="number" ld:subtype="int16_t" ld:bits="16"/>
        </ld:global-type>
        </ld:data-definition>
        """
        PROTO = """
        message entity_position_raw {
          required int32 squad_sz = 1;
        }
        """
        CPP = """
        void DFProto::describe_entity_position_raw(dfproto::entity_position_raw* proto, df::entity_position_raw* dfhack) {
          proto->set_squad_sz(dfhack->squad_size);
        }
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.sut_cpp.add_exception_rename('ld:global-type[@type-name="entity_position_raw"]/ld:field[@name="squad_size"]', 'squad_sz')
        self.sut_proto.add_exception_rename('ld:global-type[@type-name="entity_position_raw"]/ld:field[@name="squad_size"]', 'squad_sz')
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)
    
    def test_index_field(self):
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
          optional int32 next_id = 1;
        }
        """
        CPP = """
        void DFProto::describe_job_list_link(dfproto::job_list_link* proto, df::job_list_link* dfhack) {
          proto->set_next_id(dfhack->next->id);
        }
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.sut_cpp.add_exception_index('job_list_link', 'id')
        self.sut_proto.add_exception_index('job_list_link', 'id')
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)


    #
    # non-regression tests from bug fixing
    #

    def test_bugfix_pointer_with_comment(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="class-type" ld:level="0" type-name="job_handler" original-name="job_handlerst" custom-methods="true">
        <ld:field ld:level="2" ld:meta="pointer" type-name="unit" comment="List" ld:is-container="true">
          <ld:item ld:level="3" ld:meta="global" type-name="unit"/>
        </ld:field>
        <ld:field ld:level="2" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
        </ld:global-type>
        </ld:data-definition>
        """
        PROTO = """
        message job_handler {
          /* List */
          optional unit anon_1 = 1;
          required int32 anon_2 = 2;
        }
        """
        CPP = """
        void DFProto::describe_job_handler(dfproto::job_handler* proto, df::job_handler* dfhack) {
          describe_unit(proto->mutable_anon_1(), dfhack->anon_1);
          proto->set_anon_2(dfhack->anon_2);
        }
        """
        IMPORTS = ['unit']
        DFPROTO_IMPORTS = ['unit']
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)


    def test_bugfix_multiple_anon_compounds_and_fields(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="class-type" ld:level="0" type-name="job_handler" original-name="job_handlerst" custom-methods="true">
        <ld:field ld:meta="container" ld:level="1" ld:subtype="stl-vector" ld:is-container="true">
          <ld:item ld:level="2" ld:meta="pointer" ld:is-container="true">
            <ld:item ld:meta="compound" ld:level="2">
              <ld:field ld:level="3" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
            </ld:item>
          </ld:item>
        </ld:field>
        <ld:field ld:level="1" ld:meta="static-array" count="2000" ld:is-container="true">
          <ld:item ld:meta="compound" ld:level="1">
            <ld:field ld:level="2" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
          </ld:item>
        </ld:field>
        </ld:global-type>
        </ld:data-definition>
        """
        PROTO = """
        message job_handler {
          message T_anon_1 {
            required int32 anon_1 = 1;
          }
          repeated T_anon_1 anon_1 = 1; 
          message T_anon_2 {
            required int32 anon_1 = 1;
          }
          repeated T_anon_2 anon_2 = 2;
        }
        """
        CPP = """
        void DFProto::describe_job_handler(dfproto::job_handler* proto, df::job_handler* dfhack) {
          auto describe_T_anon_1 = [](dfproto::job_handler_T_anon_1* proto, df::job_handler::T_anon_1* dfhack) {
            proto->set_anon_1(dfhack->anon_1);
          };
          for (size_t i=0; i<dfhack->anon_1.size(); i++) {
            describe_T_anon_1(proto->add_anon_1(), dfhack->anon_1[i]);
          }
          auto describe_T_anon_2 = [](dfproto::job_handler_T_anon_2* proto, df::job_handler::T_anon_2* dfhack) {
            proto->set_anon_1(dfhack->anon_1);
          };
          for (size_t i=0; i<2000; i++) {
            describe_T_anon_2(proto->add_anon_2(), &dfhack->anon_2[i]);
          }
        }
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)
