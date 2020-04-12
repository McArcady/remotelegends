#!/bin/python3

import unittest
import subprocess
from lxml import etree

from global_type_renderer import GlobalTypeRenderer

OUTPUT_FNAME = 'output.proto'

class TestGlobalTypeRenderer(unittest.TestCase):

    output = ''

    @classmethod
    def setUpClass(cls):
        cls.XML = """
        <ld:data-definition xmlns:ld="ns">
        <ld:global-type ld:meta="struct-type" ld:level="0" type-name="history">
          <ld:field ld:subtype="enum" name="type" type-name="history_event_reason" base-type="int32_t" ld:level="1" ld:meta="global"/>
          <ld:field name="data" is-union="true" init-value="-1" ld:level="1" ld:meta="compound" ld:typedef-name="T_data" ld:in-union="true">
            <ld:field name="glorify_hf" ref-target="historical_figure" ld:level="2" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
            <ld:field name="artifact_is_heirloom_of_family_hfid" ref-target="historical_figure" ld:level="2" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>"historical_entity" ld:level="2" ld:meta="number" ld:subtype="int32_t" ld:bits="32"/>
          </ld:field>
          <ld:field ld:subtype="bitfield" name="modification" base-type="uint32_t" ld:level="1" ld:meta="compound" ld:typedef-name="T_modification">
            <ld:field name="dungeon" ld:level="2" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
            <ld:field name="fortifications" ld:level="2" ld:meta="number" ld:subtype="flag-bit" ld:bits="1"/>
          </ld:field>
        </ld:global-type>        
        </ld:data-definition>
        """
        cls.PROTO = """
        /* THIS FILE WAS GENERATED. DO NOT EDIT. */
        syntax = "proto3";
        import "history_event_reason.proto";

        package df;
        message history {
          history_event_reason type = 1;
          oneof data {
            int32 glorify_hf = 2;
            int32 artifact_is_heirloom_of_family_hfid = 3;
          }
          message T_modification {
            enum mask {
              dungeon = 0x0;
              fortifications = 0x1;
            }
            fixed32 flags = 1;
          }
          T_modification modification = 4;
        }
        """

    def assertStructEqual(self, str1, str2):
        self.assertEqual(''.join(str1.split()), ''.join(str2.split()), str1+'/'+str2)
    
    def test_render(self):
        root = etree.fromstring(self.XML)
        sut = GlobalTypeRenderer(root[0], 'ns')
        self.assertEqual(sut.get_type_name(), 'history')
        out = sut.render()
        self.assertStructEqual(out, self.PROTO)

    def test_render_to_file(self):
        root = etree.fromstring(self.XML)
        sut = GlobalTypeRenderer(root[0], 'ns')
        fname = sut.render_to_file('./')
        self.assertEqual(fname, 'history.proto')
        with open(fname, 'r') as fil:
            self.assertStructEqual(fil.read(), self.PROTO)
        subprocess.check_call(['protoc -I. -o%s.pb  %s' % (fname, fname)], shell=True)
