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
    # test global types
    #
    
    def test_render_global_type_enum(self):
        # FIXME: enums do not need a cpp file anymore
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
        self.assertEqual(len(self.sut.dfproto_imports), 0)
        self.assertStructEqual(out, """
 	void DFProto::describe_ui_advmode_menu(dfproto::ui_advmode_menu* proto, df::ui_advmode_menu* dfhack)
	{
	  *proto = *dfhack;
	}
        """)
        self.output += out + '\n'
    
#     def test_render_global_type_enum_with_values(self):
#         XML = """
#         <ld:data-definition xmlns:ld="ns">
#         <ld:global-type ld:meta="enum-type" ld:level="0" type-name="conflict_level">
#           <enum-item name="None" value="-1"/>
#           <enum-item name="Encounter"/>
#           <enum-item name="Horseplay"/>
#           <enum-item value="-3"/>
#         </ld:global-type>
#         </ld:data-definition>
#         """
#         root = etree.fromstring(XML)
#         out = self.sut.render_type(root[0])
#         self.assertEqual(len(self.sut.imports), 0)
#         self.assertStructEqual(out, """
#         enum conflict_level {
#           conflict_level_Encounter = 0;
#           conflict_level_Horseplay = 1;
#           conflict_level_None = -1;
#           conflict_level_anon_m3 = -3;
#         }
#         """)
#         self.output += out + '\n'

            
#     def test_render_global_type_struct_with_primitive_fields(self):
#         XML = """
#         <ld:data-definition xmlns:ld="ns">
#         <ld:global-type ld:meta="struct-type" ld:level="0" type-name="conversation1">
#           <ld:field name="conv_title" ld:level="1" ld:meta="primitive" ld:subtype="stl-string"/>
#           <ld:field name="unk_30" ref-target="unit" ld:level="1" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
#         </ld:global-type>
#         </ld:data-definition>
#         """
#         root = etree.fromstring(XML)
#         out = self.sut.render_type(root[0])
#         self.assertEqual(len(self.sut.imports), 0)
#         self.assertStructEqual(out, """
#         message conversation1 {
#           string conv_title = 1;
#           int32 unk_30 = 2;
#         }
#         """)
#         self.output += out + '\n'
    
#     def test_render_global_type_struct_with_recursive_ref(self):
#         XML = """
#         <ld:data-definition xmlns:ld="ns">
#         <ld:global-type ld:meta="struct-type" ld:subtype="df-linked-list-type" ld:level="0" type-name="job_list_link" item-type="job">
#           <ld:field name="next" type-name="job_list_link" ld:level="1" ld:meta="pointer" ld:is-container="true">
#             <ld:item ld:level="2" ld:meta="global" type-name="job_list_link"/>
# </ld:field>
#         </ld:global-type>
#         </ld:data-definition>
#         """
#         root = etree.fromstring(XML)
#         out = self.sut.render_type(root[0])
#         # avoid recursive import
#         self.assertEqual(len(self.sut.imports), 0)
#         self.assertStructEqual(out, """
#         message job_list_link {
#           int32 next_ref = 1;
#         }
#         """)
#         self.output += out + '\n'

    # def test_render_global_type_struct_with_list_link(self):
    #     XML = """
    #     <ld:data-definition xmlns:ld="ns">
    #     <ld:global-type ld:meta="class-type" ld:level="0" type-name="projectile" original-name="projst" df-list-link-type="proj_list_link" df-list-link-field="link" key-field="id">
    #       <ld:field ld:level="1" ld:meta="pointer" name="link" type-name="proj_list_link" ld:is-container="true">
    #         <ld:item ld:level="2" ld:meta="global" type-name="proj_list_link"/>
    #     </ld:field>
    #     </ld:global-type>
    #     </ld:data-definition>
    #     """
    #     root = etree.fromstring(XML)
    #     out = self.sut.render_type(root[0])
    #     # avoid recursive import
    #     self.assertEqual(len(self.sut.imports), 0)
    #     self.assertStructEqual(out, """
    #     message projectile {
    #       int32 link_ref = 1;
    #     }
    #     """)
    #     self.output += out + '\n'

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
        root = etree.fromstring(XML)
        out = self.sut.render_type(root[0])
        self.assertEqual(list(self.sut.imports), ['history_event_reason'])
        self.assertEqual(list(self.sut.dfproto_imports), [])
        self.assertStructEqual(out, """
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
        """)

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
        root = etree.fromstring(XML)
        out = self.sut.render_type(root[0])
        self.assertListEqual(list(self.sut.imports), ['nemesis_record'])
        self.assertEqual(list(self.sut.dfproto_imports), [])
        self.assertStructEqual(out, """
        void DFProto::describe_conversation(dfproto::conversation* proto, df::conversation* dfhack)
        {
	  for (size_t i=0; i<dfhack->unk_54.size(); i++) {
	    proto->add_unk_54_ref(dfhack->unk_54[i]->id);
	  }
        }
        """)
        self.output += out + '\n'

    def test_render_global_type_struct_with_inheritance(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="class-type" ld:level="0" type-name="proj_itemst" inherits-from="projectile">
          <ld:field ld:level="1" ld:meta="pointer" name="item" type-name="item" ld:is-container="true"><ld:item ld:level="2" ld:meta="global" type-name="item"/></ld:field>
        </ld:global-type>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_type(root[0])
        self.assertListEqual(sorted(list(self.sut.imports)), ['item'])
        self.assertEqual(list(self.sut.dfproto_imports), ['projectile'])
        self.assertStructEqual(out, """
        void DFProto::describe_proj_itemst(dfproto::proj_itemst* proto, df::proj_itemst* dfhack)
        {
	  describe_projectile(proto->mutable_parent(), dfhack);
	  proto->set_item_ref(dfhack->item->id);
        }
        """)

    def test_render_global_type_struct(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="struct-type" ld:level="0" type-name="campfire">
          <ld:field type-name="coord" name="pos" ld:level="1" ld:meta="global"/>
          <ld:field name="timer" ld:level="1" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
        </ld:global-type>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_type(root[0])
        self.assertListEqual(list(self.sut.imports), [])
        self.assertListEqual(list(self.sut.dfproto_imports), ['coord'])
        self.assertStructEqual(out, """
        void DFProto::describe_campfire(dfproto::campfire* proto, df::campfire* dfhack)
        {
	  describe_coord(proto->mutable_pos(), &dfhack->pos);
	  proto->set_timer(dfhack->timer);
        }
        """)

    # def test_render_global_type_class(self):
    #     XML = """
    #     <ld:data-definition xmlns:ld="ns">
    #     <ld:global-type ld:meta="class-type" ld:level="0" type-name="adventure_movement_optionst" comment="comment">
    #       <ld:field name="dest" type-name="coord" ld:level="1" ld:meta="global"/>
    #       <ld:field name="source" type-name="coord" ld:level="1" ld:meta="global"/>
    #       <virtual-methods>
    #         <vmethod ld:level="1"><ld:field ld:level="2" ld:meta="pointer" ld:is-container="true"/></vmethod>
    #         <vmethod ld:level="1"/>
    #       </virtual-methods>
    #     </ld:global-type>
    #     </ld:data-definition>
    #     """
    #     root = etree.fromstring(XML)
    #     out = self.sut.render_cpp(root[0])
    #     self.assertListEqual(list(self.sut.imports), ['coord'])
    #     self.assertStructEqual(out, """
    #     void DFProto::describeCoord(dfproto::coord* proto, df::coord* dfhack)
    #     /* comment */
    #     message adventure_movement_optionst {
    #       coord dest = 1;
    #       coord source = 2;
    #     }
    #     """)

    def test_render_global_type_bitfield(self):
        # FIXME: bitfields do not need a cpp file anymore        
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
        self.assertEqual(len(self.sut.dfproto_imports), 0)
        self.assertStructEqual(out, """
        void DFProto::describe_announcement_flags(dfproto::announcement_flags* proto, df::announcement_flags* dfhack)
        {
          proto->set_flags(dfhack->whole);
        }
        """)
        self.output += out + '\n'

    
    # #
    # # test fields and local types
    # #

    # def test_render_field_local_enum(self):
    #     XML = """
    #     <ld:data-definition xmlns:ld="ns">
    #       <ld:field ld:subtype="enum" base-type="int32_t" name="state" ld:level="1" ld:meta="compound" ld:typedef-name="T_state">
    #         <enum-item name="started"/>
    #         <enum-item name="active"/>
    #       </ld:field>
    #     </ld:data-definition>
    #     """
    #     root = etree.fromstring(XML)
    #     out = self.sut.render_field(root[0])
    #     self.assertEqual(len(self.sut.imports), 0)
    #     self.assertStructEqual(out, """
    #     enum T_state {
    #       state_started = 0;
    #       state_active = 1;
    #     }
    #     T_state state = 1;
    #     """)

    def test_render_field_global_enum(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:subtype="enum" name="type" base-type="int32_t" type-name="talk_choice_type" ld:level="1" ld:meta="global"/>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_field(root[0])
        self.assertListEqual(list(self.sut.imports), ['talk_choice_type'])
        self.assertListEqual(list(self.sut.dfproto_imports), [])
        self.assertStructEqual(out, """
        proto->set_type(static_cast<dfproto::talk_choice_type>(dfhack->type));
        """)

    def test_render_field_pointer_to_primitive_type(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:level="1" ld:meta="pointer" since="v0.47.02" ld:is-container="true"/>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_field(root[0])
        self.assertListEqual(list(self.sut.imports), [])
        self.assertEqual(list(self.sut.dfproto_imports), [])
        self.assertStructEqual(out, """
        // ignored pointer to unknown type
        """)
        self.output += out + '\n'

    def test_render_field_anon_pointer(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:level="1" ld:meta="pointer" name="p_mattype" type-name="int16_t" ld:is-container="true"><ld:item ld:level="2" ld:meta="number" ld:subtype="int16_t" ld:bits="16"/>
          </ld:field>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        self.sut.global_type_name = 'entity_claim_mask'
        out = self.sut.render_field(root[0])
        self.assertListEqual(list(self.sut.imports), [])
        self.assertEqual(list(self.sut.dfproto_imports), [])
        self.assertStructEqual(out, """
        proto->set_p_mattype(*dfhack->p_mattype);
        """)
        self.output += out + '\n'

    def test_render_field_pointer_to_anon_compound(self):
        # FIXME: probably need indirection for dfhack->map -> *dfhack->map
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
        self.sut.global_type_name = 'entity_claim_mask'
        out = self.sut.render_field(root[0])
        self.assertListEqual(list(self.sut.imports), [])
        self.assertEqual(list(self.sut.dfproto_imports), [])
        self.assertStructEqual(out, """
        auto describe_T_map = [](dfproto::entity_claim_mask_T_map* proto, df::entity_claim_mask::T_map* dfhack) {
	  for (size_t i=0; i<dfhack->entities.size(); i++) {
	    proto->add_entities(dfhack->entities[i]);
	  }
        };
        describe_T_map(proto->mutable_map(), dfhack->map);
        """)
        self.output += out + '\n'
    
    def test_render_field_job_list_link(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:meta="container" ld:level="1" ld:subtype="df-linked-list" name="list" type-name="job_list_link" ld:is-container="true">
          <ld:item ld:level="2" ld:meta="global" type-name="job_list_link"/>
        </ld:field>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_field(root[0])
        self.assertEqual(list(self.sut.imports), [])
        self.assertEqual(list(self.sut.dfproto_imports), ['job_list_link'])
        self.assertStructEqual(out, """
        describe_job_list_link(proto->mutable_list(), &dfhack->list);
        """)
    
    # def test_render_field_container_pointer_to_primitive(self):
    #     XML = """
    #     <ld:data-definition xmlns:ld="ns">
    #     <ld:field ld:meta="container" ld:level="1" ld:subtype="stl-vector" name="name_singular" pointer-type="stl-string" ld:is-container="true">
    #       <ld:item ld:meta="pointer" ld:is-container="true" ld:level="2" type-name="stl-string">
    #         <ld:item ld:level="3" ld:meta="primitive" ld:subtype="stl-string"/>
    #       </ld:item>
    #     </ld:field>
    #     </ld:data-definition>
    #     """
    #     root = etree.fromstring(XML)
    #     out = self.sut.render_field(root[0])
    #     self.assertEqual(len(self.sut.imports), 0)
    #     self.assertStructEqual(out, """
    #     repeated string name_singular = 1;
    #     """)
    
    # def test_render_field_container_pointer_to_global(self):
    #     XML = """
    #     <ld:data-definition xmlns:ld="ns">
    #     <ld:field ld:meta="container" ld:level="1" ld:subtype="stl-vector" name="children" pointer-type="building" ld:is-container="true">
    #       <ld:item ld:meta="pointer" ld:is-container="true" ld:level="2" type-name="building">
    #       <ld:item ld:level="3" ld:meta="global" type-name="building"/>
    #     </ld:item>
    #     </ld:field>
    #     </ld:data-definition>
    #     """
    #     root = etree.fromstring(XML)
    #     out = self.sut.render_field(root[0])
    #     self.assertEqual(list(self.sut.imports), [])
    #     self.assertStructEqual(out, """
    #     repeated int32 children_ref = 1;
    #     """)

    def test_render_field_bitfield(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:subtype="bitfield" name="flags_0" type-name="knowledge_scholar_flags_0" ld:level="2" ld:meta="global"/>
        </ld:data-definition>
        """
        root = etree.fromstring(XML)
        out = self.sut.render_field(root[0])
        self.assertEqual(list(self.sut.imports), ['knowledge_scholar_flags_0'])
        self.assertEqual(len(self.sut.dfproto_imports), 0)
        self.assertStructEqual(out, """
        proto->mutable_flags_0()->set_flags(dfhack->flags_0.whole);
        """)

    # def test_render_field_local_compound(self):
    #     XML = """
    #     <ld:data-definition xmlns:ld="ns">
    #       <ld:field name="unk" ld:level="1" ld:meta="compound" ld:typedef-name="T_unk">
    #         <ld:field ld:level="2" ld:meta="pointer" name="event" type-name="entity_event" ld:is-container="true">
    #           <ld:item ld:level="3" ld:meta="global" type-name="entity_event"/>
    #         </ld:field>
    #         <ld:field ld:level="2" ld:meta="number" ld:subtype="int32_t" ld:bits="32" ld:anon-name="anon_2"/>
    #       </ld:field>
    #     </ld:data-definition>
    #     """
    #     root = etree.fromstring(XML)
    #     out = self.sut.render_field(root[0])
    #     self.assertEqual(len(self.sut.imports), 0)
    #     self.assertStructEqual(out, """
    #     message T_unk {
    #       int32 event_ref = 1;
    #       int32 anon_2 = 2;
    #     }
    #     T_unk unk = 1;
    #     """)

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
        self.sut.global_type_name = 'type_name'
        out = self.sut.render_field(root[0])
        self.assertEqual(list(self.sut.imports), ['item_type'])
        self.assertStructEqual(out, """
        auto describe_T_anon_1 = [](dfproto::type_name_T_anon_1* proto, df::type_name::T_anon_1* dfhack) {
          proto->set_x(dfhack->x);
          proto->set_item_type(static_cast<dfproto::item_type>(dfhack->item_type));
        };
        describe_T_anon_1(proto->mutable_anon_1(), dfhack->anon_1);
        """)


    # def test_render_field_anon_compound_union(self):
    #     XML = """
    #     <ld:data-definition xmlns:ld="ns">
    #       <ld:field ld:anon-compound="true" is-union="true" ld:level="3" ld:meta="compound">
    #         <ld:field name="fps" ld:level="3" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
    #         <ld:field ld:anon-compound="true" ld:level="3" ld:meta="compound">
    #           <ld:field name="x" ld:level="3" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
    #           <ld:field name="y" ld:level="3" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
    #         </ld:field>
    #         <ld:field ld:subtype="enum" base-type="int16_t" name="item_type" type-name="item_type" ld:level="3" ld:meta="global"/>
    #       </ld:field>
    #     </ld:data-definition>
    #     """        
    #     root = etree.fromstring(XML)
    #     out = self.sut.render_field(root[0])
    #     self.assertEqual(list(self.sut.imports), ['item_type'])
    #     self.assertStructEqual(out, """
    #     message T_anon_2 {
    #       int32 x = 1;
    #       int32 y = 2;
    #     }
    #     oneof anon {
    #       int32 fps = 1;
    #       T_anon_2 anon_2 = 2;
    #       item_type item_type = 3;
    #     }
    #     """)

    # def test_render_field_anon_bitfield(self):
    #     XML = """
    #     <ld:data-definition xmlns:ld="ns">
    #     <ld:field ld:subtype="bitfield" since="v0.42.01" ld:level="1" ld:meta="compound" ld:anon-name="anon_3" ld:typedef-name="T_anon_3">
    #       <ld:field name="petition_not_accepted" comment="this gets unset by accepting a petition" ld:level="2" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
    #       <ld:field name="convicted_accepted" comment="convicted for PositionCorruption/accepted for Location" ld:level="2" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
    #     </ld:field>
    #     </ld:data-definition>
    #     """
    #     root = etree.fromstring(XML)
    #     out = self.sut.render_field(root[0])
    #     self.assertEqual(len(self.sut.imports), 0)
    #     self.assertStructEqual(out, """
    #     message T_anon_3 {
    #       enum mask {
    #         petition_not_accepted = 0x0; /* this gets unset by accepting a petition */
    #         convicted_accepted = 0x1; /* convicted for PositionCorruption/accepted for Location */
    #       }
    #       fixed32 flags = 1;
    #     }
    #     T_anon_3 anon_3 = 1;
    #     """)

    # def test_render_field_bitfield(self):
    #     XML = """
    #     <ld:data-definition xmlns:ld="ns">
    #     <ld:field ld:subtype="bitfield" name="gems_use" ld:level="1" ld:meta="compound">
    #       <ld:field name="noun" ld:level="2" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
    #       <ld:field name="adj" ld:level="2" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
    #       <ld:field name="adj_noun" ld:level="2" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
    #     </ld:field>
    #     </ld:data-definition>
    #     """
    #     root = etree.fromstring(XML)
    #     out = self.sut.render_field(root[0])
    #     self.assertEqual(len(self.sut.imports), 0)
    #     self.assertStructEqual(out, """
    #     message T_gems_use {
    #       enum mask {
    #         noun = 0x0;
    #         adj = 0x1;
    #         adj_noun = 0x2;
    #       }
    #       fixed32 flags = 1;
    #     }
    #     T_gems_use gems_use = 1;
    #     """)


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
