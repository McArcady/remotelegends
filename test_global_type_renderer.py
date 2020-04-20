#!/bin/python3

import unittest
import subprocess
import os
from lxml import etree

from global_type_renderer import GlobalTypeRenderer


class TestGlobalTypeRenderer(unittest.TestCase):

    def setUp(self):
        self.XML = """
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
        self.PROTO = """
        /* THIS FILE WAS GENERATED. DO NOT EDIT. */
        syntax = "proto2";
        import "history_event_reason.proto";

        package dfproto;
        message history_event_reason_info {
          required history_event_reason type = 1;
          oneof data {
            int32 glorify_hf = 2;
            int32 artifact_is_heirloom_of_family_hfid = 3;
          }
        }
        """
        self.CPP = """
        /* THIS FILE WAS GENERATED. DO NOT EDIT. */
        #include "history_event_reason_info.h"
        #include "df/history_event_reason.h"
        #include "history_event_reason.pb.h"

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
        self.H = """
        /* THIS FILE WAS GENERATED. DO NOT EDIT. */
        #include "Export.h"
        #include <stdint.h>
        #include "df/history_event_reason_info.h"
        #include "history_event_reason_info.pb.h"

        namespace DFProto {
	  void describe_history_event_reason_info(dfproto::history_event_reason_info* proto, df::history_event_reason_info* dfhack);
        }
        """
        self.maxDiff = None
        self.delete_me = []

    def tearDown(self):
        for f in self.delete_me:
            os.remove(f)
        

    def assertStructEqual(self, str1, str2):
        self.assertEqual(''.join(str1.split()), ''.join(str2.split()), str1+'/'+str2)
    
    def test_render_proto(self):
        root = etree.fromstring(self.XML)
        sut = GlobalTypeRenderer(root[0], 'ns')
        self.assertEqual(sut.get_type_name(), 'history_event_reason_info')
        self.assertEqual(sut.get_meta_type(), 'struct-type')
        out = sut.render_proto()
        self.assertStructEqual(out, self.PROTO)

    def test_render_cpp(self):
        root = etree.fromstring(self.XML)
        sut = GlobalTypeRenderer(root[0], 'ns')
        self.assertEqual(sut.get_type_name(), 'history_event_reason_info')
        out = sut.render_cpp()
        self.assertStructEqual(out, self.CPP)

    def test_render_h(self):
        root = etree.fromstring(self.XML)
        sut = GlobalTypeRenderer(root[0], 'ns')
        self.assertEqual(sut.get_type_name(), 'history_event_reason_info')
        out = sut.render_h()
        self.assertStructEqual(out, self.H)

    def test_render_to_files(self):
        root = etree.fromstring(self.XML)
        sut = GlobalTypeRenderer(root[0], 'ns')
        fnames = sut.render_to_files('./', './', './')
        self.delete_me = fnames
        # check and compile proto
        with open(fnames[0], 'r') as fil:
            self.assertStructEqual(fil.read(), self.PROTO)
#        subprocess.check_call(['protoc -I. -o%s.pb  %s' % (fnames[0], fnames[0])], shell=True)
        # check .h
        with open(fnames[2], 'r') as fil:
            self.assertStructEqual(fil.read(), self.H)
        # check and compile cpp
        with open(fnames[1], 'r') as fil:
            self.assertStructEqual(fil.read(), self.CPP)
#        subprocess.check_call(['g++ -c -Wall -DLINUX_BUILD -lprotobuf -Iprotogen/ -I../dfhack/library/include %s' % (fnames[1])], shell=True)