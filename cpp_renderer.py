import sys
import traceback

from abstract_renderer import AbstractRenderer


class Context:
    
    def __init__(self, name=None, ident=None):
        self.name = name
        self.ident = ident or ''


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
            name, name)
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

    def render_simple_field(self, xml, ctx):
        name = self.get_name(xml)
        return '  ' + 'proto->set_%s(dfhack->%s);\n' % (
            name[0], name[1]
        )

    def render_pointer(self, xml, ctx):
        if not ctx.name:
            ctx.name = self.get_name(xml)[0]
        tname = xml.get('type-name')
        if tname == None:
            if len(xml):
                return self.render_field(xml[0], ctx)
            else:
                # pointer to anon type
                return '  // ignored pointer to unknown type'
        if CppRenderer.is_primitive_type(tname):
            return '  ' + 'proto->set_%s(*dfhack->%s);\n' % (
                ctx.name, ctx.name
            )
        self.dfproto_imports.add(tname)
        return '  ' + 'proto->set_%s_ref(dfhack->%s->id);\n' % (
            ctx.name, ctx.name
        )

    def render_container(self, xml, ctx):
        if xml.get(f'{self.ns}subtype') == 'df-linked-list':
            return self.render_global(xml)
        if xml.get(f'{self.ns}subtype') == 'df-flagarray':
            return '// flagarrays not converted yet\n'
        proto_name = name = self.get_name(xml)[0]
        dfhack_name = self.get_name(xml)[1]
        key = ''
        deref = False
        tname = xml.get('pointer-type')
        if tname:
            if CppRenderer.is_primitive_type(tname):
                deref = True
            else:
                self.dfproto_imports.add(tname)
                proto_name = name + '_ref'
                key = '->id'
        if not tname:
            tname = xml.get('type-name')
        if tname == 'pointer':
            tname = 'int32'
            name += '_ref'
        elif tname == None and len(xml):
            if xml[0].get(f'{self.ns}subtype') == 'bitfield':
                key = '.whole'
                proto_name = name + '()->set_flags'
            else:
                return self.render_field(xml[0], Context(name))
        if tname == 'bytes':
            return '  // type of %s not supported\n' % (name)
        out = """
        for (size_t i=0; i<dfhack->%s.size(); i++) {
          proto->add_%s(%sdfhack->%s[i]%s);
        }""" % ( dfhack_name, proto_name, '*' if deref else '', dfhack_name, key )
        return out
    
    def render_global(self, xml, ctx=None):
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

    def render_compound(self, xml, ctx):
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

        if not ctx.name:
            ctx.name = self.get_name(xml)[0]
        tname = self.get_typedef_name(xml, ctx.name)
        out  = self.copy().render_anon_compound(xml, ctx.name)
        out += '  ' + 'describe_%s(proto->mutable_%s(), &dfhack->%s);\n' % (
            tname, ctx.name, ctx.name
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
        

    # main renderer

    def render_field(self, xml, ctx=None):
        if not ctx:
            ctx = Context()
        return self.render_field_impl(xml, ctx)

    def render_type(self, xml):
        # high-order type name
        self.global_type_name = xml.get('type-name')
        return self.render_type_impl(xml)
    
    def render_prototype(self, xml):
        tname = xml.get('type-name')
        return 'void describe_%s(%s::%s* proto, df::%s* dfhack);' % (
            tname, self.proto_ns, tname, tname
        )
