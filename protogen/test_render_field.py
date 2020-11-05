#!/bin/python3

import unittest
from lxml import etree

from cpp_renderer import CppRenderer
from proto_renderer import ProtoRenderer


class TestRenderField(unittest.TestCase):
            
    def setUp(self):
        self.sut_proto = ProtoRenderer('ns')
        self.sut_cpp = CppRenderer('ns', 'dfproto', 'DFProto')
        self.maxDiff=  None

    def assertStructEqual(self, str1, str2):
        self.assertEqual(''.join(str1.split()), ''.join(str2.split()), str1+'/'+str2)

    def check_rendering(self, XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS, TYPE=None):
        xml = etree.fromstring(XML)[0]
        out = self.sut_proto.render_field(xml)
        self.assertStructEqual(out, PROTO)
        self.assertEqual(list(self.sut_proto.imports), IMPORTS)
        self.sut_cpp.outer_types = [TYPE]
        out = self.sut_cpp.render_field(xml)
        self.assertStructEqual(out, CPP)
        self.assertEqual(list(self.sut_cpp.imports), IMPORTS)
        self.assertEqual(list(self.sut_cpp.dfproto_imports), DFPROTO_IMPORTS)


    #
    # enum
    #

    def test_render_field_enum(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:subtype="enum" name="type" base-type="int32_t" type-name="talk_choice_type" ld:level="1" ld:meta="global"/>
        </ld:data-definition>
        """
        PROTO = """
        required talk_choice_type type = 1;
        """
        CPP = """
        proto->set_type(static_cast<dfproto::talk_choice_type>(dfhack->type));
        """
        IMPORTS = ['talk_choice_type']
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)
    
    def test_render_field_local_enum(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:subtype="enum" base-type="int32_t" name="state" ld:level="1" ld:meta="compound" ld:typedef-name="T_state">
            <enum-item name="started"/>
            <enum-item name="active"/>
          </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        enum T_state {
          T_state_started = 0;
          T_state_active = 1;
        }
        required T_state state = 1;
        """
        CPP = """
        proto->set_state(static_cast<dfproto::mytype_T_state>(dfhack->state));
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS, 'mytype')
    
    def test_render_field_anon_enum(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:subtype="enum" base-type="int32_t" name="role" ld:level="1" ld:meta="compound">
          <enum-item name="Other" comment="eat, drink, pickup equipment"/>
          <enum-item name="Reagent"/>
        </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        enum T_role {
          T_role_Other = 0; /* eat, drink, pickup equipment */
          T_role_Reagent = 1;
        }
        required T_role role = 1;
        """
        CPP = """
        proto->set_role(static_cast<dfproto::mytype_T_role>(dfhack->role));
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS, 'mytype')


    #
    # bitfield
    #

    def test_render_field_bitfield(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:subtype="bitfield" name="flags_0" type-name="knowledge_scholar_flags_0" ld:level="2" ld:meta="global"/>
        </ld:data-definition>
        """
        PROTO = """
        required knowledge_scholar_flags_0 flags_0 = 1;
        """
        CPP = """
        proto->mutable_flags_0()->set_flags(dfhack->flags_0.whole);
        """
        IMPORTS = ['knowledge_scholar_flags_0']
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    def test_render_field_local_bitfield(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:subtype="bitfield" name="gems_use" ld:level="1" ld:meta="compound">
          <ld:field name="noun" ld:level="2" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
          <ld:field name="adj" ld:level="2" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
          <ld:field name="adj_noun" ld:level="2" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
        </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        message T_gems_use {
          enum mask {
            noun = 0x0;
            adj = 0x1;
            adj_noun = 0x2;
          }
          required fixed32 flags = 1;
        }
        required T_gems_use gems_use = 1;
        """
        CPP = """
        proto->mutable_gems_use()->set_flags(dfhack->gems_use.whole);
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    def test_render_field_anon_bitfield(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:subtype="bitfield" since="v0.42.01" ld:level="1" ld:meta="compound" ld:anon-name="anon_3" ld:typedef-name="T_anon_3">
          <ld:field name="petition_not_accepted" comment="this gets unset by accepting a petition" ld:level="2" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
          <ld:field name="convicted_accepted" comment="convicted for PositionCorruption/accepted for Location" ld:level="2" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
        </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        message T_anon_3 {
          enum mask {
            petition_not_accepted = 0x0; /* this gets unset by accepting a petition */
            convicted_accepted = 0x1; /* convicted for PositionCorruption/accepted for Location */
          }
          required fixed32 flags = 1;
        }
        required T_anon_3 anon_3 = 1;
        """
        CPP = """
        proto->mutable_anon_3()->set_flags(dfhack->anon_3.whole);
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    
    #
    # df-linked-list
    #
        
    def test_render_field_job_list_link(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:meta="container" ld:level="1" ld:subtype="df-linked-list" name="list" type-name="job_list_link" ld:is-container="true">
          <ld:item ld:level="2" ld:meta="global" type-name="job_list_link"/>
        </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        required job_list_link list = 1;
        """
        CPP = """
        describe_job_list_link(proto->mutable_list(), &dfhack->list);
        """
        IMPORTS = ['job_list_link']
        DFPROTO_IMPORTS = ['job_list_link']
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)


    #
    # container
    #
    
    def test_render_field_container_vector_of_primitives(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:meta="container" ld:level="1" ld:subtype="stl-vector" type-name="int16_t" name="talk_choices" ld:is-container="true">
            <ld:item ld:level="2" ld:meta="number" ld:subtype="int16_t" ld:bits="16"/>
        </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        repeated int32 talk_choices = 1;
        """
        CPP = """
	for (size_t i=0; i<dfhack->talk_choices.size(); i++) {
	  proto->add_talk_choices(dfhack->talk_choices[i]);
	}
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    def test_render_field_container_array_of_primitives(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:level="1" ld:meta="static-array" name="words" count="7" ld:is-container="true">
          <ld:item ref-target="language_word" ld:level="2" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
        </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        repeated int32 words = 1;
        """
        CPP = """
        for (size_t i=0; i<7; i++) {
          proto->add_words(dfhack->words[i]);
        }
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)
    
    def test_render_field_container_array_of_global_type(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:level="1" ld:meta="static-array" name="armorstand_pos" count="6" ld:is-container="true">
            <ld:item type-name="coord" ld:level="2" ld:meta="global"/>
        </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        repeated coord armorstand_pos = 1;
        """
        CPP = """
	for (size_t i=0; i<6; i++) {
          describe_coord(proto->add_armorstand_pos(), &dfhack->armorstand_pos[i]);
	}
        """
        IMPORTS = ['coord']
        DFPROTO_IMPORTS = ['coord']
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)
    
    def test_render_field_container_of_anon_compounds(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:level="2" ld:meta="static-array" name="approx" count="40" since="v0.40.01" comment="10 * cosine/sine of the index in units of 1/40 of a circle" ld:is-container="true">
          <ld:item ld:meta="compound" ld:level="2">
            <ld:field name="cos" ld:level="3" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
            <ld:field name="sin" ld:level="3" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
          </ld:item>                
        </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        /* 10 * cosine/sine of the index in units of 1/40 of a circle */
        message T_approx {
          required int32 cos = 1;
          required int32 sin = 2;
        }
        repeated T_approx approx = 1;
        """
        CPP = """
        auto describe_T_approx = [](dfproto::mytype_T_approx* proto, df::mytype::T_approx* dfhack) {
          proto->set_cos(dfhack->cos);
          proto->set_sin(dfhack->sin);
        };
        for (size_t i=0; i<40; i++) {
          describe_T_approx(proto->add_approx(), &dfhack->approx[i]);
        }
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS, 'mytype')

    def test_render_field_container_of_bitfields(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:meta="container" ld:level="1" ld:subtype="stl-vector" name="killed_undead" ld:is-container="true">
            <ld:item ld:subtype="bitfield" base-type="uint16_t" ld:level="2" ld:meta="compound">
                <ld:field name="zombie" ld:level="3" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
                <ld:field name="ghostly" ld:level="3" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
            </ld:item>
        </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        message T_killed_undead {
          enum mask {
            zombie = 0x0;
            ghostly = 0x1;
          }
          required fixed32 flags = 1;
        }
        repeated T_killed_undead killed_undead = 1;
        """
        CPP = """
        for (size_t i=0; i<dfhack->killed_undead.size(); i++) {
          proto->add_killed_undead()->set_flags(dfhack->killed_undead[i].whole);
        }
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)
    
    def test_render_field_container_of_empty_bitfields(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:meta="container" ld:level="1" ld:subtype="stl-vector" name="can_connect" ld:is-container="true">
          <ld:item ld:subtype="bitfield" type-name="machine_conn_modes" ld:level="2" ld:meta="global"/>
        </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        message T_can_connect {
          required fixed32 flags = 1;
        }
        repeated T_can_connect can_connect = 1;
        """
        CPP = """
        for (size_t i=0; i<dfhack->can_connect.size(); i++) {
          proto->add_can_connect()->set_flags(dfhack->can_connect[i].whole);
        }
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    def test_render_field_container_of_enums(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:level="1" ld:meta="static-array" name="parts_of_speech" count="7" ld:is-container="true">
          <ld:item ld:subtype="enum" base-type="int16_t" type-name="part_of_speech" ld:level="2" ld:meta="global"/>
        </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        repeated part_of_speech parts_of_speech = 1;
        """
        CPP = """
        for (size_t i=0; i<7; i++) {
          proto->add_parts_of_speech(static_cast<dfproto::part_of_speech>(dfhack->parts_of_speech[i]));
        }
        """
        IMPORTS = ['part_of_speech']
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    # suffix '_type' is automatically interpreted as an enum type
    def test_render_field_container_of_enums_with_suffix_type(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:level="2" ld:meta="static-array" name="relationship" type-name="vague_relationship_type" count="6" comment="unused elements are uninitialized" ld:is-container="true">
          <ld:item ld:level="3" ld:meta="global" type-name="vague_relationship_type"/>
        </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        /* unused elements are uninitialized */
        repeated vague_relationship_type relationship = 1;
        """
        CPP = """
	for (size_t i=0; i<6; i++) {
          proto->add_relationship(static_cast<dfproto::vague_relationship_type>(dfhack->relationship[i]));
	}
        """
        IMPORTS = ['vague_relationship_type']
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    def test_render_field_container_of_local_enums(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:meta="container" ld:level="1" ld:subtype="stl-vector" name="options" ld:is-container="true">
            <ld:item ld:subtype="enum" base-type="int32_t" name="options" ld:level="2" ld:meta="compound">
                <enum-item name="Return"/>
                <enum-item name="Save"/>
            </ld:item>
        </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        enum T_options {
          T_options_Return = 0;
          T_options_Save = 1;
        }
        repeated T_options options = 1;
        """
        CPP = """
        for (size_t i=0; i<dfhack->options.size(); i++) {
          proto->add_options(static_cast<dfproto::mytype_T_options>(dfhack->options[i]));
        }
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS, 'mytype')
    
    def test_render_field_empty_container(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:meta="container" ld:level="1" ld:subtype="stl-vector" since="v0.40.01" comment="not saved" ld:is-container="true"/>
        </ld:data-definition>
        """
        PROTO = """
        /* ignored container anon_1 */
        """
        CPP = """
        /* ignored empty container anon_1 */
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)


    #
    # container of pointers
    #

    def test_render_field_container_of_pointers_to_primitive(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:meta="container" ld:level="1" ld:subtype="stl-vector" name="name_singular" pointer-type="stl-string" ld:is-container="true">
          <ld:item ld:meta="pointer" ld:is-container="true" ld:level="2" type-name="stl-string">
            <ld:item ld:level="3" ld:meta="primitive" ld:subtype="stl-string"/>
          </ld:item>
        </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        repeated string name_singular = 1;
        """
        CPP = """
	for (size_t i=0; i<dfhack->name_singular.size(); i++) {
          if (dfhack->name_singular[i] != NULL) proto->add_name_singular(*dfhack->name_singular[i]);
	}
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)
    
    def test_render_field_container_of_pointers_to_global_type(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:meta="container" ld:level="1" ld:subtype="stl-vector" name="children" pointer-type="building" ld:is-container="true">
          <ld:item ld:meta="pointer" ld:is-container="true" ld:level="2" type-name="building">
            <ld:item ld:level="3" ld:meta="global" type-name="building"/>
          </ld:item>
        </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        repeated building children = 1;
        """
        CPP = """
	for (size_t i=0; i<dfhack->children.size(); i++) {
          if (dfhack->children[i] != NULL) describe_building(proto->add_children(), dfhack->children[i]);
	}
        """
        IMPORTS = ['building']
        DFPROTO_IMPORTS = ['building']
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    def test_render_field_container_of_pointers_to_anon_compound(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:meta="container" ld:level="1" ld:subtype="stl-vector" name="postings" comment="entries never removed" ld:is-container="true">
            <ld:item ld:level="2" ld:meta="pointer" ld:is-container="true">
              <ld:item ld:meta="compound" ld:level="2">
                <ld:field name="idx" comment="equal to position in vector" ld:level="3" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
              </ld:item>
            </ld:item>
        </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        /* entries never removed */
        message T_postings {
          required int32 idx = 1; /* equal to position in vector */
        }
        repeated T_postings postings = 1;
        """
        CPP = """
        auto describe_T_postings = [](dfproto::mytype_T_postings* proto, df::mytype::T_postings* dfhack) {
          proto->set_idx(dfhack->idx);
        };
        for (size_t i=0; i<dfhack->postings.size(); i++) {
          if (dfhack->postings[i] != NULL) describe_T_postings(proto->add_postings(), dfhack->postings[i]);
        }
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS, 'mytype')

    def test_render_field_array_of_vectors(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:level="2" ld:meta="static-array" name="layer_x" count="5" ld:is-container="true">
            <ld:item ld:meta="container" ld:level="3" ld:subtype="stl-vector" type-name="int16_t" ld:is-container="true">
              <ld:item ld:level="4" ld:meta="number" ld:subtype="int16_t" ld:bits="16"/>
            </ld:item>
        </ld:field>
        </ld:data-definition>
        """
        # FIXME: fix after refactoring
        PROTO = """
        /* ignored container of containers layer_x */
        """
        CPP =  """
        /* ignored container of containers layer_x */
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    def test_render_field_array_of_arrays(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:level="1" ld:meta="static-array" name="supermovie_sound_time" count="16" ld:is-container="true">
            <ld:item ld:level="2" ld:meta="static-array" count="200" type-name="int32_t" ld:is-container="true">
              <ld:item ld:level="3" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
              </ld:item>
        </ld:field>
        </ld:data-definition>
        """
        # FIXME: fix after refactoring
        PROTO = """
        /* ignored container of containers supermovie_sound_time */
        """
        CPP =  """
        /* ignored container of static-arrays supermovie_sound_time */
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    @unittest.skip('FIXME')
    def test_render_field_container_of_pointers_to_containers(self):
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
        # FIXME: fix after refactoring
        PROTO = """
        /* ignored container of containers region_masks */
        """
        CPP =  """
        /* ignored container of containers region_masks */
        """
        CPP = None
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)


    #
    # pointer
    #

    def test_render_field_pointer_to_global_type(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:level="1" ld:meta="pointer" name="profile" type-name="workshop_profile" ld:is-container="true">
          <ld:item ld:level="2" ld:meta="global" type-name="workshop_profile"/>
        </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        optional workshop_profile profile = 1;
        """
        CPP =  """
        if (dfhack->profile != NULL) describe_workshop_profile(proto->mutable_profile(), dfhack->profile);
        """
        IMPORTS = ['workshop_profile']
        DFPROTO_IMPORTS = ['workshop_profile']
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    def test_render_field_anon_pointer(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:level="1" ld:meta="pointer" name="p_mattype" type-name="int16_t" ld:is-container="true">
            <ld:item ld:level="2" ld:meta="number" ld:subtype="int16_t" ld:bits="16"/>
          </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        optional int32 p_mattype = 1;
        """
        CPP =  """
        if (dfhack->p_mattype != NULL) proto->set_p_mattype(*dfhack->p_mattype);
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

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
        PROTO = """
        message T_map {
          repeated int32 entities = 1;
        }
        optional T_map map = 1;
        """
        CPP = """
        auto describe_T_map = [](dfproto::entity_claim_mask_T_map* proto, df::entity_claim_mask::T_map* dfhack) {
	  for (size_t i=0; i<dfhack->entities.size(); i++) {
	    proto->add_entities(dfhack->entities[i]);
	  }
        };
        if (dfhack->map != NULL) describe_T_map(proto->mutable_map(), dfhack->map);
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS, 'entity_claim_mask')

    def test_render_field_pointer_to_array(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:level="1" ld:meta="pointer" name="temporary_trait_changes" comment="sum of inebriation or so personality changing effects" ld:is-container="true">
          <ld:item ld:level="2" ld:meta="static-array" type-name="int16_t" name="traits" count="50" index-enum="personality_facet_type" ld:is-container="true">
            <ld:item ld:level="3" ld:meta="number" ld:subtype="int16_t" ld:bits="16"/>
          </ld:item>
        </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        /* sum of inebriation or so personality changing effects */
        repeated int32 temporary_trait_changes = 1;
        """
        CPP =  """
        if (dfhack->temporary_trait_changes != NULL) for (size_t i=0; i<50; i++) {
          proto->add_temporary_trait_changes((*dfhack->temporary_trait_changes)[i]);
        }
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    def test_render_field_pointer_to_vector(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:level="1" ld:meta="pointer" name="spheres" ld:is-container="true">
            <ld:item ld:meta="container" ld:level="2" ld:subtype="stl-vector" ld:is-container="true">
                <ld:item ld:subtype="enum" base-type="int16_t" type-name="sphere_type" ld:level="3" ld:meta="global"/>
            </ld:item>
        </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        repeated sphere_type spheres = 1;
        """
        CPP =  """
        if (dfhack->spheres != NULL) for (size_t i=0; i<dfhack->spheres->size(); i++) {
          proto->add_spheres(static_cast<dfproto::sphere_type>((*dfhack->spheres)[i]));
        }
        """
        IMPORTS = ['sphere_type']
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS)

    def test_render_field_pointer_to_unknown_type(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:level="1" ld:meta="pointer" since="v0.47.02" ld:is-container="true"/>
        </ld:data-definition>
        """
        PROTO = """
        /* ignored pointer to unknown type */
        """
        CPP = """
        /* ignored pointer to unknown type */
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS, 'entity_claim_mask')
    
    
    #
    # compound
    #

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
        PROTO = """
        message T_unk {
          optional entity_event event = 1;
          required int32 anon_2 = 2;
        }
        required T_unk unk = 1;
        """
        CPP = """
        auto describe_T_unk = [](dfproto::mytype_T_unk* proto, df::mytype::T_unk* dfhack) {
          if (dfhack->event != NULL) describe_entity_event(proto->mutable_event(), dfhack->event);
          proto->set_anon_2(dfhack->anon_2);
        };
        describe_T_unk(proto->mutable_unk(), &dfhack->unk);
        """
        IMPORTS = ['entity_event']
        DFPROTO_IMPORTS = ['entity_event']
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS, 'mytype')

    def test_render_field_anon_compound(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
          <ld:field ld:anon-compound="true" ld:level="1" ld:meta="compound">
            <ld:field name="x" ld:level="2" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
            <ld:field ld:subtype="enum" base-type="int16_t" name="item_type" type-name="item_type" ld:level="2" ld:meta="global"/>
          </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        message T_anon {
          required int32 x = 1;
          required item_type item_type = 2;
        }
        """
        CPP = """
        auto describe_T_anon_1 = [](dfproto::mytype_T_anon_1* proto, df::mytype::T_anon_1* dfhack) {
          proto->set_x(dfhack->x);
          proto->set_item_type(static_cast<dfproto::item_type>(dfhack->item_type));
        };
        describe_T_anon_1(proto->mutable_anon_1(), &dfhack->anon_1);
        """
        IMPORTS = ['item_type']
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS, 'mytype')


    #
    # union
    #

    def test_render_field_union_of_compounds(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field name="abuse_data" is-union="true" ld:level="1" ld:meta="compound">
            <ld:field name="Piled" ld:level="2" ld:meta="compound">
                <ld:field ld:subtype="enum" name="pile_type" base-type="int32_t" ld:level="3" ld:meta="compound">
                    <enum-item name="GrislyMound"/>
                    <enum-item name="GrotesquePillar"/>
                    <enum-item name="GruesomeSculpture"/>
                </ld:field>
            </ld:field>
            <ld:field name="Flayed" ld:level="2" ld:meta="compound">
                <ld:field name="structure" ref-target="abstract_building" ld:level="3" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
            </ld:field>
        </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        message T_piled {
          enum T_pile_type {
            T_pile_type_GrislyMound = 0;
            T_pile_type_GrotesquePillar = 1;
            T_pile_type_GruesomeSculpture = 2;
          }
          required T_pile_type pile_type = 1;
        }
        message T_flayed {
          required int32 structure = 1;
        }
        oneof abuse_data {
          T_piled piled = 1;
          T_flayed flayed = 2;
        }
        """
        # FIXME
        CPP = """
        /* failed to find a discriminator for union T_abuse_data */
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS, 'mytype')


    #
    # conversion
    #

    def test_render_field_with_converted_type(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field name="name" type-name="language_name" export-as="string" ld:level="1" ld:meta="global"/>
        </ld:data-definition>
        """
        PROTO = """
        required string name = 1;
        """
        CPP = """
        convert_language_name_to_string(&dfhack->name, proto->mutable_name());
        """
        IMPORTS = []
        DFPROTO_IMPORTS = ['conversion']
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS, 'mytype')


        
    #
    # non-regression tests from bug fixing
    #

    def test_bugfix_anon_container_of_anon_compounds(self):
        XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:field ld:level="1" ld:meta="static-array" count="2000" ld:is-container="true">
          <ld:item ld:meta="compound" ld:level="1">
            <ld:field ld:level="2" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
          </ld:item>
        </ld:field>
        </ld:data-definition>
        """
        PROTO = """
        message T_anon_1 {
          required int32 anon_1 = 1;
        }
        repeated T_anon_1 anon_1 = 1;
        """
        CPP = """
        auto describe_T_anon_1 = [](dfproto::mytype_T_anon_1* proto, df::mytype::T_anon_1* dfhack) {
          proto->set_anon_1(dfhack->anon_1);
        };
        for (size_t i=0; i<2000; i++) {
          describe_T_anon_1(proto->add_anon_1(), &dfhack->anon_1[i]);
        }
        """
        IMPORTS = []
        DFPROTO_IMPORTS = []
        self.check_rendering(XML, PROTO, CPP, IMPORTS, DFPROTO_IMPORTS, 'mytype')
