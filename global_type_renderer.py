import sys
import traceback

from proto_renderer import ProtoRenderer
from cpp_renderer import CppRenderer


class GlobalTypeRenderer:

    def __init__(self, xml, ns, proto_ns='dfproto'):
        self.ns = ns
        self.proto_ns = proto_ns
        self.version = 2
        self.exceptions = []
        self.xml = xml
        assert self.xml.tag == '{%s}global-type' % (self.ns)

    def set_proto_version(self, ver):
        self.version = ver
        return self

    def set_exceptions_file(self, fname):
        with open(fname, 'r') as fil:
            for line in fil:
                tokens = line.strip().split(' ')
                if not tokens:
                    continue
                if tokens[0] == 'rename':
                    self.exceptions.append(tokens)
        
    
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
        rdr = ProtoRenderer(self.ns, self.proto_ns).set_version(self.version)
        for tokens in self.exceptions:
            rdr.add_exception_rename(tokens[1], tokens[2])
        typout = rdr.render_type(self.xml)
        out = '/* THIS FILE WAS GENERATED. DO NOT EDIT. */\n'
        out += 'syntax = "proto%d";\n' % (self.version)
        for imp in rdr.imports:
            out += 'import \"%s.proto\";\n' % (imp)
        # TODO: declare package 'df'
        out += '\n' + typout
        return out

    def render_cpp(self):
        rdr = CppRenderer(self.ns, self.proto_ns, 'DFProto')
        for tokens in self.exceptions:
            rdr.add_exception_rename(tokens[1], tokens[2])
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

    def render_h(self):
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

    def render_to_files(self, proto_out, cpp_out, h_out):
        proto_name = self.get_type_name() + '.proto'
        with open(proto_out + '/' + proto_name, 'w') as fil:
            fil.write(self.render_proto())
        if self.get_meta_type() in ['struct-type', 'class-type']:
            cpp_name = self.get_type_name() + '.cpp'
            with open(cpp_out + '/' + cpp_name, 'w') as fil:
                fil.write(self.render_cpp())
            h_name = self.get_type_name() + '.h'
            with open(h_out + '/' + h_name, 'w') as fil:
                fil.write(self.render_h())
            return (proto_name, cpp_name, h_name)
        return [proto_name]
