import sys
import traceback

from proto_renderer import ProtoRenderer
from cpp_renderer import CppRenderer


class GlobalTypeRenderer:

    def __init__(self, xml, ns, proto_ns='dfproto'):
        self.ns = ns
        self.proto_ns = proto_ns
        self.xml = xml
        assert self.xml.tag == '{%s}global-type' % (self.ns)

    def get_type_name(self):
        tname = self.xml.get('type-name')
        if not tname:
            tname = self.xml.get('name')
        assert tname
        return tname           

    def get_meta_type(self):
        return self.xml.get('{%s}meta' % (self.ns))
    

    # main renderer

    def render_proto(self):
        try:
            rdr = ProtoRenderer(self.ns, self.proto_ns)
            typout = rdr.render_type(self.xml)
            out = '/* THIS FILE WAS GENERATED. DO NOT EDIT. */\n'
            out += 'syntax = "proto3";\n'
            for imp in rdr.imports:
                out += 'import \"%s.proto\";\n' % (imp)
            # TODO: declare package 'df'
            out += '\n' + typout
            return out
        except Exception as e:
            _,value,tb = sys.exc_info()
            print('error rendering type %s at line %d: %s' % (self.get_type_name(), self.xml.sourceline if self.xml.sourceline else 0, e))
            traceback.print_tb(tb)
            return ""

    def render_cpp(self):
        try:
            rdr = CppRenderer(self.ns, self.proto_ns, 'DFProto')
            typout = rdr.render_type(self.xml)
            out = '/* THIS FILE WAS GENERATED. DO NOT EDIT. */\n'
            out += '#include \"%s.h\"\n' % (self.get_type_name())
            for imp in rdr.imports:
                out += '#include \"df/%s.h\"\n' % (imp)
                out += '#include \"%s.pb.h\"\n' % (imp)
            for imp in rdr.dfproto_imports:
                out += '#include \"%s.h\"\n' % (imp)
            out += '\n' + typout
            return out
        except Exception as e:
            _,value,tb = sys.exc_info()
            print('error rendering type %s at line %d: %s' % (self.get_type_name(), self.xml.sourceline if self.xml.sourceline else 0, e))
            traceback.print_tb(tb)
            return ""

    def render_h(self):
        try:
            rdr = CppRenderer(self.ns, self.proto_ns, 'DFProto')
            out  = '/* THIS FILE WAS GENERATED. DO NOT EDIT. */\n'
            out += '#include "Export.h"\n'
            out += '#include <stdint.h>\n'
            out += '#include \"df/%s.h\"\n' % (self.get_type_name())
            out += '#include \"%s.pb.h\"\n' % (self.get_type_name())
            out += '\nnamespace DFProto {\n'
            out += '  %s\n' % (rdr.render_prototype(self.xml))
            out += '}\n'
            return out
        except Exception as e:
            _,value,tb = sys.exc_info()
            print('error rendering type %s at line %d: %s' % (self.get_type_name(), self.xml.sourceline if self.xml.sourceline else 0, e))
            traceback.print_tb(tb)
            return ""

    def render_to_files(self, path):
        proto_name = self.get_type_name() + '.proto'
        with open(path + '/' + proto_name, 'w') as fil:
            fil.write(self.render_proto())
        if self.get_meta_type() in ['struct-type', 'class-type']:
            cpp_name = self.get_type_name() + '.cpp'
            with open(path + '/' + cpp_name, 'w') as fil:
                fil.write(self.render_cpp())
            h_name = self.get_type_name() + '.h'
            with open(path + '/' + h_name, 'w') as fil:
                fil.write(self.render_h())
            return proto_name, cpp_name, h_name
        return [proto_name]
