from collections import defaultdict
import sys
import traceback


class CppRenderer:

    def __init__(self, xml_ns, proto_ns, cpp_ns):
        # namespaces: xml, protobuf, cpp
        self.ns = '{'+xml_ns+'}'
        self.proto_ns = proto_ns
        self.cpp_ns = cpp_ns
        # external dfhack & protobuf dependencies
        self.imports = set()
        # external dfproto dependencies
        self.dfproto_imports = set()
        # guess of the discriminant element for union
        self.last_enum_descr = None
        
    TYPES = defaultdict(lambda: None, {
        k:v for k,v in {
            'bool': 'bool',
            'int8_t': 'int32',
            'int16_t': 'int32',
            'int32_t': 'int32',
            'int64_t': 'int64',
            'uint8_t': 'uint32',
            'uint16_t': 'uint32',
            'uint32_t': 'uint32',
            'uint64_t': 'uint64',
            'long': 'int64',
            's-float': 'float',
            'd-float': 'double',
            'stl-string': 'string',
            'static-string': 'string',
            'ptr-string': 'string',
            'stl-fstream': 'bytes',
            'padding': 'bytes',
        }.items()})

    @staticmethod
    def convert_type(typ):
        return CppRenderer.TYPES[typ]

    @staticmethod
    def is_primitive_type(typ):
        return typ in CppRenderer.TYPES.keys()

    def get_name(self, xml, value=1):
        name = xml.get('name')
        if not name:
            name = xml.get(f'{self.ns}anon-name')
        if value < 0:
            value = 'm'+str(-value)
        if not name:
            name = 'anon_' + str(value)
        return name

    def get_typedef_name(self, xml, name):
        tname = xml.get(f'{self.ns}typedef-name')
        if not tname:
            tname = 'T_' + name
        return tname

    def ident(self, xml):
        ident = xml.get(f'{self.ns}level') or 1
        return '  ' * int(ident)
        
    def _render_line(self, xml, tname, value, name=None):
        out = ''
        if tname:
            out += tname + ' '
        if not name:
            name = self.get_name(xml, value)
        out += name + ' = ' + str(value) + ';'
        comment = xml.get('comment')
        if comment:
            out += ' /* ' + comment + '*/'
        return out + '\n'

    
    # enumerations

    def _render_enum_item(self, xml, tname, value, prefix=''):
        name = self.get_name(xml, value)
        out = prefix + name + ' = ' + str(value) + ';'
        comment = xml.get('comment')
        if comment:
            out += ' /* ' + comment + '*/'
        return out + '\n'

    def render_enum_type(self, xml, tname=None, prefix=None, extra_ident=''):
        if not tname:            
            tname = xml.get('type-name')
        assert tname
        return """
        void %s::describe_%s(%s::%s* proto, df::%s* dfhack) {
          *proto = *dfhack;
        }
        """ % ( self.cpp_ns, tname, self.proto_ns, tname, tname )

    def render_enum(self, xml, value=1):
        # record enum descriptor in case it is needed later as a discriminator for an union
        self.last_enum_descr = xml
        name = self.get_name(xml, value)
        tname = xml.get('type-name')
        out = '  proto->set_%s(static_cast<dfproto::%s>(dfhack->%s));\n' % (
            name, tname, name
        )
        return out

    
    # fields & containers

    def _convert_tname(self, tname):
        if CppRenderer.is_primitive_type(tname):
            tname = CppRenderer.convert_type(tname)
        elif tname:
            self.imports.add(tname)
        else:
            tname = 'bytes'
        return tname

    def render_simple_field(self, xml, value=1):
        # tname = xml.get(f'{self.ns}subtype')
        # if tname == 'enum' or tname == 'bitfield':
        #     tname = xml.get('type-name')
        #     self.imports.add(tname)
        # else:
        #     tname = self._convert_tname(tname)
        name = self.get_name(xml, value)
        return '  ' + 'proto->set_%s(dfhack->%s);\n' % (
            name, name
        )

    def render_pointer(self, xml, value=1, name=None):
        if not name:
            name = self.get_name(xml, value)
        tname = xml.get('type-name')
        if tname == None and len(xml):
            return self.render_field(xml[0], value, name)
        self.imports.add(tname)
        return '  ' + 'proto->set_%s_ref(dfhack->%s->id);\n' % (
            name, name
        )

    def render_container(self, xml, value=1):
        name = self.get_name(xml)
        tname = xml.get('pointer-type')
        if tname and not CppRenderer.is_primitive_type(tname):
            self.imports.add(tname)
            return """
            for (size_t i=0; i<dfhack->%s.size(); i++) {
	      proto->add_%s_ref(dfhack->%s[i]->id);
	    }\n""" % ( name, name, name )
        if not tname:
            tname = xml.get('type-name')
        if tname == 'pointer':
            tname = 'int32'
        else:
            tname = self._convert_tname(tname)
        if tname == 'bytes':
            return '  // type of %s not supported' % (name)
        out = '  for (size_t i=0; i<dfhack->%s.size(); i++) {\n    proto->add_%s(dfhack->%s[i]);\n  }\n' % ( name, name, name )
        return out
    
    def render_global(self, xml, value=1):
        name = self.get_name(xml, value)
        tname = xml.get('type-name')
        assert tname
        subtype = xml.get(f'{self.ns}subtype')
        if subtype == 'enum':
            self.imports.add(tname)
            return self.render_enum(xml)
        if subtype == 'bitfield':
            self.imports.add(tname)
            return self.render_bitfield(xml, value)
        self.dfproto_imports.add(tname)
        return '  ' + 'describe_%s(proto->mutable_%s(), &dfhack->%s);\n' % (
            tname, name, name
        )
    
    
    # structs

    def render_struct_type(self, xml, tname=None):
        if not tname:
            tname = xml.get('type-name')
        out = 'void %s::describe_%s(%s::%s* proto, df::%s* dfhack) {\n' % (
            self.cpp_ns, tname, self.proto_ns, tname, tname
        )
        parent = xml.get('inherits-from')
        if parent:
            out += '  ' + 'describe_%s(proto->mutable_parent(), dfhack);\n' % ( parent )
            self.dfproto_imports.add(parent)
        for item in xml.findall(f'{self.ns}field'):
            name = self.get_name(item)
            tname = item.get(f'{self.ns}subtype') or item.get('type-name')
            out += self.render_field(item)
        out += '}\n'
        return out

    def render_anon_compound(self, xml, name=None):
        tname = self.get_typedef_name(xml, name)
        # lambda
        out  = '  ' + 'auto describe_%s = [](dfproto::%s_%s* proto, df::%s::%s* dfhack) {\n' % ( tname, self.global_type_name, tname, self.global_type_name, tname )
        for item in xml.findall(f'{self.ns}field'):
            name = self.get_name(item)
            tname = item.get(f'{self.ns}subtype') or item.get('type-name')
            out += self.render_field(item)
        out += '};\n'
        return out

    def render_compound(self, xml, value=1, name=None):
        subtype = xml.get(f'{self.ns}subtype')
        if subtype == 'enum':
            return self.render_enum(xml, value)
        if subtype == 'bitfield':
            return self.render_bitfield(xml, value)
        
        anon = xml.get(f'{self.ns}anon-compound')
        union = xml.get('is-union')
        if union == 'true':
            if anon == 'true':
                return self.render_union(xml, 'anon', value)
            return self.render_union(xml, value)
        if anon == 'true':
            return self.render_anon_compound(xml)

        if not name:
            name = self.get_name(xml, value)
        tname = self.get_typedef_name(xml, name)
        out  = self.render_anon_compound(xml, name)
        out += '  ' + 'describe_%s(proto->mutable_%s(), *dfhack->%s);\n' % (
            tname, name, name
        )
        return out
    

    # unions

    def render_union(self, xml, tname, value=1):
        name = self.get_name(xml)
        if self.last_enum_descr == None:
            return '// failed to find a discriminator for union %s\n' % (self.get_typedef_name(xml, name))
        tname = self.last_enum_descr.get('type-name')
        out  = '  switch (dfhack->type) {\n'
        for item in xml.findall(f'{self.ns}field'):
            iname = self.get_name(item,value)
            out += '    case ::df::enums::%s::%s:\n' % (tname, iname)
            out += '      proto->set_%s(dfhack->%s.%s);\n' % (iname, name, iname)
            out += '      break;\n'
        out += '    default:\n'
        out += '      proto->clear_%s();\n' % (name)
        out += '  }\n'
        return out

    
    # bitfields

    def render_bitfield_masks(self, xml):
        out = self.ident(xml) + 'enum mask {\n'
        value = 0
        for item in xml.findall(f'{self.ns}field'):
            out += self.ident(xml) + '  %s = 0x%x;' % (
                self.get_name(item,value), value
            )
            comment = item.get('comment')
            if comment:
                out += ' /* ' + comment + '*/'
            out += '\n'
            value += 1
        out += self.ident(xml) + '}\n'
        return out
    
    def render_bitfield_type(self, xml, tname=None):
        if not tname:
            tname = xml.get('type-name')
        return """
        void %s::describe_%s(%s::%s* proto, df::%s* dfhack) {
          proto->set_flags(dfhack->whole);
        }
        """ % ( self.cpp_ns, tname, self.proto_ns, tname, tname )
    
    def render_bitfield(self, xml, value):
        name = self.get_name(xml, value)
        tname = self.get_typedef_name(xml, name)
        out = '  proto->mutable_%s()->set_flags(dfhack->%s.whole);\n' % (
            name, name
        )
        return out
        

    # main renderer

    def render_field(self, xml, value=1, name=None):
        # TODO: handle comments for all types
        meta = xml.get(f'{self.ns}meta')
        if not meta or meta == 'compound':
            return self.render_compound(xml, value, name)
        if meta == 'primitive' or meta == 'number' or meta == 'bytes':
            return self.render_simple_field(xml)
        elif meta == 'container' or meta == 'static-array':
            return self.render_container(xml, value)
        elif meta == 'global':
            return self.render_global(xml, value)
        elif meta == 'pointer':
            return self.render_pointer(xml, value, name)
        raise Exception('not supported: '+xml.tag+': meta='+str(meta))

    def render_type(self, xml):
        # high-order type name
        self.global_type_name = xml.get('type-name')
        meta = xml.get(f'{self.ns}meta')
        try:
            out = ''
            if meta == 'bitfield-type':
                return out + self.render_bitfield_type(xml)
            elif meta == 'enum-type':
                return out + self.render_enum_type(xml)
            elif meta == 'class-type':
                return out + self.render_struct_type(xml)
            elif meta == 'struct-type':
                return out + self.render_struct_type(xml)
            raise Exception('not supported: '+xml.tag+': meta='+str(meta))
            
        except Exception as e:
            _,value,tb = sys.exc_info()
            print('error rendering element %s (meta=%s,name=%s) at line %d: %s' % (
                xml.tag,
                meta if meta else '<unknown>',
                self.get_name(xml, 0),
                xml.sourceline if xml.sourceline else 0, e
            ))
            traceback.print_tb(tb)
            return ""

    def render_prototype(self, xml):
        tname = xml.get('type-name')
        return 'void describe_%s(%s::%s* proto, df::%s* dfhack);' % (
            tname, self.proto_ns, tname, tname
        )
