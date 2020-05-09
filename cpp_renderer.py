import sys
import traceback

from abstract_renderer import AbstractRenderer


class Context:
    
    def __init__(self, name=None, ident=None):
        self.name = name
        self.ident = ident or 0
        self.deref = False

    def set_deref(self, deref):
        self.deref = deref
        return self

    def dec_ident(self):
        self.ident -= 1
        return self

    def inc_ident(self):
        self.ident += 1
        return self


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
        AbstractRenderer.copy(self, copy)
        copy.imports = self.imports
        copy.dfproto_imports = self.dfproto_imports
        copy.global_type_name = self.global_type_name
        return copy

    
    # enumerations

    def render_type_enum(self, xml, tname=None):
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
        tname = xml.get('type-name')
        if tname:
            prefix = ''
        else:
            # local enum
            tname = self.get_typedef_name(xml, name[0])
            prefix = self.global_type_name + '_'
        out = self.ident(xml) + 'proto->set_%s(static_cast<dfproto::%s%s>(dfhack->%s));\n' % (name[0], prefix, tname, name[1])
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
        
    def render_field_bitfield(self, xml):
        name = self.get_name(xml)[0]
        tname = self.get_typedef_name(xml, name)
        out = self.ident(xml) + 'proto->mutable_%s()->set_flags(dfhack->%s.whole);\n' % (name, name)
        return out

    
    # simple fields

    def _convert_tname(self, tname):
        if self.is_primitive_type(tname):
            tname = self.convert_type(tname)
        elif tname:
            self.imports.add(tname)
        else:
            tname = 'bytes'
        return tname

    def render_field_simple(self, xml, ctx):
        name = self.get_name(xml)
        return self.ident(xml, ctx.ident) + 'proto->set_%s(dfhack->%s);\n' % (
            name[0], name[1]
        )
    
    def render_field_global(self, xml, ctx):
        if not ctx.name:
            ctx.name = self.get_name(xml)[0]
        tname = xml.get('type-name')
        assert tname
        subtype = xml.get(f'{self.ns}subtype')
        if subtype == 'enum':
            self.imports.add(tname)
            return self.render_field_enum(xml)
        if subtype == 'bitfield':
            self.imports.add(tname)
            return self.render_field_bitfield(xml)
        if subtype == 'df-linked-list':
            self.imports.add(tname)
        self.dfproto_imports.add(tname)
        self.imports.add(tname)
        return self.ident(xml, ctx.ident) + 'describe_%s(proto->mutable_%s(), %sdfhack->%s);\n' % (
            tname, ctx.name, '&' if not ctx.deref else '', ctx.name
        )


    # pointers and containers
    
    def render_pointer(self, xml, ctx):
        if not ctx.name:
            ctx.name = self.get_name(xml)[0]
        tname = xml.get('type-name')
        if self.is_primitive_type(tname):
            return self.ident(xml) + 'proto->set_%s(*dfhack->%s);\n' % (
                ctx.name, ctx.name
            )
        # replace type with an id ?
        for k,v in iter(self.exceptions_index):
            if k == tname:
                self.dfproto_imports.add(tname)
                return self.ident(xml) + 'proto->set_%s_%s(dfhack->%s->%s);\n' % (
                    ctx.name, v, ctx.name,v 
                )
        if len(xml):
            return self.render_field(xml[0], ctx.set_deref(True).dec_ident())
        else:
            # pointer to anon type
            return self.ident(xml) + '/* ignored pointer to unknown type */\n'

    def render_container(self, xml, ctx):
        subtype = xml.get(f'{self.ns}subtype')
        if subtype == 'df-linked-list':
            return self.render_field_global(xml, ctx)
        if subtype == 'df-flagarray':
            return '/* flagarrays not converted yet */\n'
        if ctx.name:
            proto_name = dfhack_name = name = ctx.name
        else:
            proto_name = name = self.get_name(xml)[0]
            dfhack_name = self.get_name(xml)[1]
        key = ''
        deref = False
        out = ''
        item_str = None
        tname = xml.get('pointer-type')
        if tname:
            if self.is_primitive_type(tname):
                deref = True
            else:
                self.imports.add(tname)
                self.dfproto_imports.add(tname)
                for k,v in iter(self.exceptions_index):
                    if k == tname:
                        proto_name = name + '_ref'
                        key = '->'+v
                if not key:
                    item_str = 'describe_%s(proto->add_%s(), dfhack->%s[i]);' % (
                        tname, proto_name, name
                    )                
        if not tname and len(xml):
            subtype = xml[0].get(f'{self.ns}subtype')
            tname = xml[0].get('type-name')
            if subtype == 'bitfield':
                key = '.whole'
                proto_name = name + '()->set_flags'
            elif subtype == 'enum' or tname and tname.endswith('_type'):
                if tname:
                    self.imports.add(tname)
                else:
                    tname = self.global_type_name + '_T_' + name
                item_str = 'proto->add_%s(static_cast<dfproto::%s>(dfhack->%s[i]));' % (
                    name, tname, name
                )
            elif self.is_primitive_type(subtype):
                item_str = 'proto->add_%s(dfhack->%s[i]);' % (
                    name, name
                )
            else:
                meta = xml[0].get(f'{self.ns}meta')
                if meta == 'pointer':
                    if len(xml[0]) == 0:
                        return self.ident(xml) + '/* ignored empty container %s*/\n' % (name)
                    out += self.render_anon_compound(xml[0][0], name)
                    item_str = 'describe_%s(proto->add_%s(), dfhack->%s[i]);' % (
                        'T_'+name, name, name
                    )                    
                elif meta == 'compound':
                    out += self.render_anon_compound(xml[0], name)
                    item_str = 'describe_%s(proto->add_%s(), &dfhack->%s[i]);' % (
                        'T_'+name, name, name
                    )
                elif meta=='container' or meta=='static-array':
                    return '/* ignored container of containers %s*/\n' % (name)
                else:
                    tname = xml[0].get('type-name')
                    if self.is_primitive_type(tname):
                        return self.render_field(xml[0], Context(name))
                    self.imports.add(tname)
                    self.dfproto_imports.add(tname)
                    item_str = 'describe_%s(proto->add_%s(), &dfhack->%s[i]);' % (
                        tname, name, name
                    )
        elif tname == None:
            return self.ident(xml) + '/* ignored container %s*/\n' % (name)
        if tname == 'bytes':
            return self.ident(xml) + '/* type of %s not supported*/\n' % (name)
        if not item_str:
            item_str = 'proto->add_%s(%sdfhack->%s[i]%s);' % (
                proto_name, '*' if deref else '', dfhack_name, key
            )
        count = xml.get('count')
        if not count:
            count = 'dfhack->%s.size()' % (dfhack_name)
        out += self.ident(xml) + 'for (size_t i=0; i<%s; i++) {\n' % (count)
        out += self.ident(xml) + '  %s\n' % (item_str)
        out += self.ident(xml) + '}\n'
        return out
    
    
    # structs

    def render_type_struct(self, xml, tname=None):
        if not tname:
            tname = xml.get('type-name')
        out = self.ident(xml) + 'void %s::describe_%s(%s::%s* proto, df::%s* dfhack) {\n' % (
            self.cpp_ns, tname, self.proto_ns, tname, tname
        )
        value = 1
        parent = xml.get('inherits-from')
        if parent:
            out += self.ident(xml) + '  describe_%s(proto->mutable_parent(), dfhack);\n' % ( parent )
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
        out  = self.ident(xml) + 'auto describe_%s = [](dfproto::%s_%s* proto, df::%s::%s* dfhack) {\n' % ( tname, self.global_type_name, tname, self.global_type_name, tname )
        for item in xml.findall(f'{self.ns}field'):
            name = self.get_name(item)[0]
            tname = item.get(f'{self.ns}subtype') or item.get('type-name')
            out += self.render_field(item)
        out += self.ident(xml) + '};\n'
        return out

    def render_field_compound(self, xml, ctx):
        subtype = xml.get(f'{self.ns}subtype')
        if subtype == 'enum':
            return self.render_field_enum(xml)
        if subtype == 'bitfield':
            return self.render_field_bitfield(xml)
        
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
        out += self.ident(xml) + 'describe_%s(proto->mutable_%s(), %sdfhack->%s);\n' % (
            tname, ctx.name, '&' if ctx.deref is False else '', ctx.name
        )
        return out
    

    # unions

    def render_union(self, xml, tname=None):
        name = self.get_name(xml)
        if self.last_enum_descr == None:
            return '/* failed to find a discriminator for union %s*/\n' % (self.get_typedef_name(xml, name[0]))
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
