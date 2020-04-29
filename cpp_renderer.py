import sys
import traceback

from abstract_renderer import AbstractRenderer


class CppRenderer(AbstractRenderer):

    def __init__(self, xml_ns, proto_ns, cpp_ns):
        AbstractRenderer.__init__(self, xml_ns)
        # namespaces: protobuf, cpp
        self.proto_ns = proto_ns
        self.cpp_ns = cpp_ns
        # external dfhack & protobuf dependencies
        self.imports = set()
        # external dfproto dependencies
        self.dfproto_imports = set()
        # guess of the discriminant element for union
        self.last_enum_descr = None
        self.global_type_name = None

    def copy(self):
        copy = CppRenderer(self.ns, self.proto_ns, self.cpp_ns)
        copy.imports = self.imports
        copy.dfproto_imports = self.dfproto_imports
        copy.global_type_name = self.global_type_name
        return copy

    
    # enumerations

    def render_type_enum(self, xml, tname=None, extra_ident=''):
        if not tname:            
            tname = xml.get('type-name')
        assert tname
        return """
        void %s::describe_%s(%s::%s* proto, df::%s* dfhack) {
          *proto = *dfhack;
        }
        """ % ( self.cpp_ns, tname, self.proto_ns, tname, tname )

    def render_field_enum(self, xml):
        # record enum descriptor in case it is needed later as a discriminator for an union
        self.last_enum_descr = xml
        name = self.get_name(xml)
        if xml.get(f'{self.ns}typedef-name'):
            # local enum
            tname = self.get_typedef_name(xml, name)
            out = '  proto->set_%s(static_cast<dfproto::%s_%s>(dfhack->%s));\n' % (
                name[0], self.global_type_name, tname, name[1]
            )
        else:
            tname = xml.get('type-name')
            out = '  proto->set_%s(static_cast<dfproto::%s>(dfhack->%s));\n' % (
                name[0], tname, name[1]
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

    def render_simple_field(self, xml):
        name = self.get_name(xml)
        return '  ' + 'proto->set_%s(dfhack->%s);\n' % (
            name[0], name[1]
        )

    def render_pointer(self, xml, name=None):
        if not name:
            name = self.get_name(xml)[0]
        tname = xml.get('type-name')
        if tname == None:
            if len(xml):
                return self.render_field(xml[0], name)
            else:
                # pointer to anon type
                return '  // ignored pointer to unknown type'
        if CppRenderer.is_primitive_type(tname):
            return '  ' + 'proto->set_%s(*dfhack->%s);\n' % (
                name, name
            )
        self.dfproto_imports.add(tname)
        return '  ' + 'proto->set_%s_ref(dfhack->%s->id);\n' % (
            name, name
        )        

    def render_container(self, xml):
        if xml.get(f'{self.ns}subtype') == 'df-linked-list':
            return self.render_global(xml)
        name = self.get_name(xml)[0]
        tname = xml.get('pointer-type')
        if tname and not CppRenderer.is_primitive_type(tname):
#            self.imports.add(tname)
            return """
            for (size_t i=0; i<dfhack->%s.size(); i++) {
	      proto->add_%s_ref(dfhack->%s[i]->id);
	    }\n""" % ( name, name, name )
        if not tname:
            tname = xml.get('type-name')
        if tname == 'pointer':
            tname = 'int32'
            name += '_ref'
        elif tname == None and len(xml):
            return self.render_field(xml[0], name)
        else:
            tname = self._convert_tname(tname)
        if tname == 'bytes':
            return '  // type of %s not supported\n' % (name)
        out = '  for (size_t i=0; i<dfhack->%s.size(); i++) {\n    proto->add_%s(dfhack->%s[i]);\n  }\n' % ( name, name, name )
        return out
    
    def render_global(self, xml):
        name = self.get_name(xml)
        tname = xml.get('type-name')
        assert tname
        subtype = xml.get(f'{self.ns}subtype')
        if subtype == 'enum':
            self.imports.add(tname)
            return self.render_field_enum(xml)
        if subtype == 'bitfield':
            self.imports.add(tname)
            return self.render_bitfield(xml)
        if subtype == 'df-linked-list':
            self.imports.add(tname)
        self.dfproto_imports.add(tname)
        return '  ' + 'describe_%s(proto->mutable_%s(), &dfhack->%s);\n' % (
            tname, name[0], name[1]
        )
    
    
    # structs

    def render_struct_type(self, xml, tname=None):
        if not tname:
            tname = xml.get('type-name')
        out = 'void %s::describe_%s(%s::%s* proto, df::%s* dfhack) {\n' % (
            self.cpp_ns, tname, self.proto_ns, tname, tname
        )
        value = 1
        parent = xml.get('inherits-from')
        if parent:
            out += '  ' + 'describe_%s(proto->mutable_parent(), dfhack);\n' % ( parent )
            self.dfproto_imports.add(parent)
            value += 1
        for item in xml.findall(f'{self.ns}field'):
            name = self.get_name(item)[0]
            tname = item.get(f'{self.ns}subtype') or item.get('type-name')
            out += self.render_field(item)
            value += 1
        out += '}\n'
        return out

    def render_anon_compound(self, xml, name=None):
        if not name:
            name = self.get_name(xml)[0]
        tname = self.get_typedef_name(xml, name)
        # lambda
        out  = '  ' + 'auto describe_%s = [](dfproto::%s_%s* proto, df::%s::%s* dfhack) {\n' % ( tname, self.global_type_name, tname, self.global_type_name, tname )
        for item in xml.findall(f'{self.ns}field'):
            name = self.get_name(item)[0]
            tname = item.get(f'{self.ns}subtype') or item.get('type-name')
            out += self.render_field(item)
        out += '};\n'
        return out

    def render_compound(self, xml, name=None):
        subtype = xml.get(f'{self.ns}subtype')
        if subtype == 'enum':
            return self.render_field_enum(xml)
        if subtype == 'bitfield':
            return self.render_bitfield(xml)
        
        anon = xml.get(f'{self.ns}anon-compound')
        union = xml.get('is-union')
        if union == 'true':
            if anon == 'true':
                return self.render_union(xml, 'anon')
            return self.render_union(xml)

        if not name:
            name = self.get_name(xml)[0]
        tname = self.get_typedef_name(xml, name)
        out  = self.copy().render_anon_compound(xml, name)
        out += '  ' + 'describe_%s(proto->mutable_%s(), &dfhack->%s);\n' % (
            tname, name, name
        )
        return out
    

    # unions

    def render_union(self, xml, tname=None):
        name = self.get_name(xml)
        if self.last_enum_descr == None:
            return '// failed to find a discriminator for union %s\n' % (self.get_typedef_name(xml, name[0]))
        tname = self.last_enum_descr.get('type-name')
        out  = '  switch (dfhack->type) {\n'
        for item in xml.findall(f'{self.ns}field'):
            iname = self.get_name(item)
            out += '    case ::df::enums::%s::%s:\n' % (tname, iname[1])
            out += '      proto->set_%s(dfhack->%s.%s);\n' % (iname[0], name[1], iname[1])
            out += '      break;\n'
        out += '    default:\n'
        out += '      proto->clear_%s();\n' % (name[0])
        out += '  }\n'
        return out

    
    # bitfields

    def render_type_bitfield(self, xml, tname=None):
        if not tname:
            tname = xml.get('type-name')
        return """
        void %s::describe_%s(%s::%s* proto, df::%s* dfhack) {
          proto->set_flags(dfhack->whole);
        }
        """ % ( self.cpp_ns, tname, self.proto_ns, tname, tname )
    
    def render_bitfield(self, xml):
        name = self.get_name(xml)[0]
        tname = self.get_typedef_name(xml, name)
        out = '  proto->mutable_%s()->set_flags(dfhack->%s.whole);\n' % (
            name, name
        )
        return out
        

    # main renderer

    def render_field(self, xml, name=None):
        # TODO: handle comments for all types
        meta = xml.get(f'{self.ns}meta')
        if not meta or meta == 'compound':
            return self.render_compound(xml, name)
        if meta == 'primitive' or meta == 'number' or meta == 'bytes':
            return self.render_simple_field(xml)
        elif meta == 'container' or meta == 'static-array':
            return self.render_container(xml)
        elif meta == 'global':
            return self.render_global(xml)
        elif meta == 'pointer':
            return self.render_pointer(xml, name)
        raise Exception('not supported: '+xml.tag+': meta='+str(meta))

    def render_type(self, xml):
        # high-order type name
        self.global_type_name = xml.get('type-name')
        out = ''
        out = self.append_comment(xml, out) + '\n'
        meta = xml.get(f'{self.ns}meta')
        if meta == 'bitfield-type':
            return out + self.render_type_bitfield(xml)
        elif meta == 'enum-type':
            return out + self.render_type_enum(xml)
        elif meta == 'class-type':
            return out + self.render_struct_type(xml)
        elif meta == 'struct-type':
            return out + self.render_struct_type(xml)
        raise Exception('not supported: '+xml.tag+': meta='+str(meta))

    def render_prototype(self, xml):
        tname = xml.get('type-name')
        return 'void describe_%s(%s::%s* proto, df::%s* dfhack);' % (
            tname, self.proto_ns, tname, tname
        )
