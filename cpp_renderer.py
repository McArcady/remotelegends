import sys
import traceback
import copy

from abstract_renderer import AbstractRenderer


class Context:
    
    def __init__(self, names=None, ident=None):
        self.names = names
        self.ident = ident or 0
        self.deref = False
        self.value = 0

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
        self.outer_types = []

    def outer_proto_tname(self):
        return '_'.join(self.outer_types)

    def outer_dfhack_tname(self):
        return '::'.join(self.outer_types)

    def copy(self):
        mycopy = CppRenderer(self.ns, self.proto_ns, self.cpp_ns)
        AbstractRenderer.copy(self, mycopy)
        mycopy.imports = self.imports
        mycopy.dfproto_imports = self.dfproto_imports
        mycopy.outer_types = copy.copy(self.outer_types)
        return mycopy

    
    # enumerations

    def render_type_enum(self, xml, tname=None):
        raise TypeError('enum type does not need a describe function')

    def _convert_enum(self, tname, names, array=False):
        return 'proto->%s_%s(static_cast<dfproto::%s>(dfhack->%s%s));\n' % (
            'add' if array else 'set', names[0],
            tname, names[1], '[i]' if array else ''
        )

    def render_field_enum(self, xml):
        # record enum descriptor for use later as a discriminator for an union
        self.last_enum_descr = xml
        names = self.get_name(xml)
        tname = xml.get('type-name')
        if not tname:
            # local enum
            tname = self.outer_proto_tname() + '_' + self.get_typedef_name(xml, names[0])
        return self.ident(xml) + self._convert_enum(tname, names)

    
    # bitfields

    def render_type_bitfield(self, xml, tname=None):
        raise TypeError('bitfield type does not need a describe function')

    def _convert_bitfield(self, names, array=False):
        return 'proto->%s_%s()->set_flags(dfhack->%s%s.whole);\n' % (
            'add' if array else 'mutable', names[0],
            names[1], '[i]' if array else ''
        )
        
    def render_field_bitfield(self, xml):
        names = self.get_name(xml)
        return self.ident(xml) + self._convert_bitfield(names)

    
    # simple fields

    def _convert_tname(self, tname):
        if self.is_primitive_type(tname):
            tname = self.convert_type(tname)
        elif tname:
            self.imports.add(tname)
        else:
            tname = 'bytes'
        return tname

    def _convert_simple(self, names, deref=False, array=False):
        return 'proto->%s_%s(%sdfhack->%s%s);\n' % (
            'add' if array else 'set', names[0],
            '*' if deref else '', names[1],
            '[i]' if array else ''
        )

    def _convert_compound(self, tname, names, deref=True, array=False):
        return 'describe_%s(proto->%s_%s(), %sdfhack->%s%s);\n' % (
            tname,
            'add' if array else 'mutable', names[0],
            '' if deref else '&',
            names[1], '[i]' if array else ''
        )
    
    def render_field_simple(self, xml, ctx):
        names = self.get_name(xml)
        return self.ident(xml, ctx.ident) + self._convert_simple(names)
    
    def render_field_global(self, xml, ctx):
        if not ctx.names:
            ctx.names = self.get_name(xml)
        tname = xml.get('type-name')
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
        return self.ident(xml, ctx.ident) + self._convert_compound(
            tname, ctx.names, deref=ctx.deref
        )


    # pointers and containers
    
    def render_field_pointer(self, xml, ctx):
        if not ctx.names:
            ctx.names = self.get_name(xml)
        tname = xml.get('type-name')
        if self.is_primitive_type(tname):
            return self._convert_simple(ctx.names, deref=True)
        for k,v in iter(self.exceptions_index):
            if k == tname:
                # convert to an id
                self.dfproto_imports.add(tname)
                return self._convert_simple( (ctx.names[0]+'_'+v, ctx.names[1]+'->'+v) )
        if len(xml):
            return self.render_field(xml[0], ctx.set_deref(True).dec_ident())
        return self.ident(xml) + '/* ignored pointer to unknown type */\n'

    def render_field_container(self, xml, ctx):
        if ctx.names:
            names = ctx.names
        else:
            names = self.get_name(xml)
        if len(xml) == 0:
            return self.ident(xml) + '/* ignored empty container %s */\n' % (names[0])

        subtype = xml.get(f'{self.ns}subtype')
        if subtype == 'df-flagarray':
            return self.ident(xml) + '/* ignored flagarray container %s */\n' % (names[0])
        if subtype == 'df-linked-list':
            return self.render_field_global(xml, ctx)
        
        deref = False
        out = ''
        item_str = None
        tname = xml.get('pointer-type')
        if tname:            
            if tname == 'bytes':
                return self.ident(xml) + '/* ignored container of pointers to bytes %s */\n' % (names[0])
            elif self.is_primitive_type(tname):
                deref = True
            else:
                self.imports.add(tname)
                self.dfproto_imports.add(tname)
                for k,v in iter(self.exceptions_index):
                    if k == tname:
                        item_str = 'proto->add_%s_%s(%sdfhack->%s[i]->%s);' % (
                            names[0], v, '*' if deref else '', names[1], v
                        )
                if not item_str:
                    item_str = self._convert_compound(
                        tname, names, array=True
                    )
        else:
            meta = xml[0].get(f'{self.ns}meta')
            subtype = xml[0].get(f'{self.ns}subtype')
            tname = xml[0].get('type-name')
            if subtype == 'bitfield':
                item_str = self._convert_bitfield(names, array=True)
            elif subtype == 'enum' or tname and tname.endswith('_type'):
                if tname:
                    self.imports.add(tname)
                else:
                    tname = self.outer_proto_tname() + '_T_' + names[0]
                item_str = self._convert_enum(tname, names, array=True)
            elif self.is_primitive_type(subtype):
                item_str = self._convert_simple(names, array=True)
            else:
                if meta == 'pointer':
                    if len(xml[0]) == 0:
                        return self.ident(xml) + '/* ignored empty container %s */\n' % (names[0])
                    out += self._convert_anon_compound(xml[0][0], names[0])
                    item_str = self._convert_compound(
                        'T_'+names[0], names, array=True
                    )                    
                elif meta == 'compound':
                    out += self._convert_anon_compound(xml[0], names[0])
                    item_str = self._convert_compound(
                        'T_'+names[0], names, array=True, deref=False
                    )
                elif meta=='container' or meta=='static-array':
                    return '/* ignored container of %ss %s */\n' % (meta, names[0])
                else:
                    tname = xml[0].get('type-name')
                    if self.is_primitive_type(tname):
                        return self.render_field(xml[0], Context(names[0]))
                    self.imports.add(tname)
                    self.dfproto_imports.add(tname)
                    item_str = self._convert_compound(
                        tname, names, array=True, deref=False
                    )
        
        if not item_str:
            item_str = self._convert_simple(
                names, deref, array=True
            )
        count = xml.get('count')
        if not count:
            count = 'dfhack->%s.size()' % (names[1])
        out += self.ident(xml) + 'for (size_t i=0; i<%s; i++) {\n' % (count)
        out += self.ident(xml) + '  %s' % (item_str)
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
            field = self.render_field(item)
            if field.lstrip().startswith('/*'):
                continue
            out += field
            value += 1
        out += '}\n'
        return out

    def _convert_anon_compound(self, xml, name=None):
        if not name:
            name = self.get_name(xml)[0]
        tname = self.get_typedef_name(xml, name)
        rdr = self.copy()
        rdr.outer_types.append(tname)
        # lambda
        out  = self.ident(xml) + 'auto describe_%s = [](dfproto::%s* proto, df::%s* dfhack) {\n' % (
            tname, rdr.outer_proto_tname(), rdr.outer_dfhack_tname()
        )
        for item in xml.findall(f'{self.ns}field'):
            name = self.get_name(item)[0]
            tname = item.get(f'{self.ns}subtype') or item.get('type-name')
            out += rdr.render_field(item)
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

        if not ctx.names:
            ctx.names = self.get_name(xml)
        tname = self.get_typedef_name(xml, ctx.names[0])
        out  = self.copy()._convert_anon_compound(xml, ctx.names[0])
        out += self.ident(xml) + self._convert_compound(
            tname, ctx.names, ctx.deref
        )
        return out
    

    # unions

    def render_union(self, xml, tname=None):
        name = self.get_name(xml)
        if self.last_enum_descr == None:
            return '/* failed to find a discriminator for union %s */\n' % (self.get_typedef_name(xml, name[0]))
        tname = self.last_enum_descr.get('type-name')
        ename = self.get_name(self.last_enum_descr)[1]
        out  = '  switch (dfhack->%s) {\n' % (ename)
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
        self.outer_types.append(xml.get('type-name'))
        return self.render_type_impl(xml)
    
    def render_prototype(self, xml):
        tname = xml.get('type-name')
        return 'void describe_%s(%s::%s* proto, df::%s* dfhack);' % (
            tname, self.proto_ns, tname, tname
        )
