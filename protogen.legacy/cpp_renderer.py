import sys
import traceback
import copy

from abstract_renderer import AbstractRenderer


class Context:
    
    def __init__(self, value=None, names=None, ident=None):
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

    def create_context(self):
        return Context()

    def copy(self):
        mycopy = CppRenderer(self.ns, self.proto_ns, self.cpp_ns)
        AbstractRenderer.copy(self, mycopy)
        mycopy.imports = self.imports
        mycopy.dfproto_imports = self.dfproto_imports
        mycopy.outer_types = copy.copy(self.outer_types)
        return mycopy

    
    # enumerations

    def render_type_enum(self, xml, tname=None):
        if not tname:
            tname = xml.get('type-name')
            out  = self.ident(xml) + 'void %s::describe_%s(%s::%s* proto, df::%s* dfhack) {\n' % ( self.cpp_ns, tname, self.proto_ns, tname, tname )
        out += '  *proto = static_cast<dfproto::%s>(*dfhack);\n' % (tname)
        out += '}\n'
        return out;

    def _convert_enum(self, tname, names, array=False, is_ptr=False, anon=False):
        if is_ptr:
            sfield = '(*dfhack->%s)' % (names[1])
        else:
            sfield = 'dfhack->%s' % (names[1])
        if anon:
            ltname = self.copy().outer_proto_tname()+'_'+tname
        else:
            ltname = tname
        out  = 'dfproto::%s %s;\n' % (ltname, names[0])
        out += 'describe_%s(&%s, &dfhack->%s%s);\n' % (
            tname, names[0], names[1], '[i]' if array else ''
        )
        out += 'proto->%s_%s(%s);\n' % (
            'add' if array else 'set', names[0], names[0]
        )
        return out

    def render_field_enum(self, xml):
        # record enum descriptor for use later as a discriminator for an union
        self.last_enum_descr = xml
        names = self.get_name(xml)
        tname = xml.get('type-name')
        if not tname:
            # local enum
            tname = self.outer_proto_tname() + '_' + self.get_typedef_name(xml, names[0])
        return self.ident(xml) + self._convert_enum(tname, names)

    def _convert_anon_enum(self, xml, name=None):
        if not name:
            name = self.get_name(xml)[0]
        tname = self.get_typedef_name(xml, name)
        rdr = self.copy()
        rdr.outer_types.append(tname)
        # lambda
        out  = self.ident(xml) + 'auto describe_%s = [](dfproto::%s* proto, df::%s* dfhack) {\n' % (
            tname, rdr.outer_proto_tname(), rdr.outer_dfhack_tname()
        )
        out += '  *proto = static_cast<dfproto::%s>(*dfhack);\n' % (rdr.outer_proto_tname())
        out += '};\n'
        return out
    
    
    # bitfields

    def render_type_bitfield(self, xml, tname=None):
        if not tname:
            tname = xml.get('type-name')
            out  = self.ident(xml) + 'void %s::describe_%s(%s::%s* proto, df::%s* dfhack) {\n' % ( self.cpp_ns, tname, self.proto_ns, tname, tname )
        out += '  proto->set_flags(dfhack->whole);\n'
        out += '}\n'
        return out;

    def _convert_bitfield(self, tname, names, array=False):
        return 'describe_%s(proto->%s_%s(), &dfhack->%s%s);\n' % (
            tname, 'add' if array else 'mutable', names[0],
            names[1], '[i]' if array else ''
        )
        
    def render_field_bitfield(self, xml):
        names = self.get_name(xml)
        tname = self.get_typedef_name(xml)
        return self.ident(xml) + self._convert_bitfield(tname, names)

    def _convert_anon_bitfield(self, xml, name=None):
        if not name:
            name = self.get_name(xml)[0]
        tname = self.get_typedef_name(xml, name)
        rdr = self.copy()
        rdr.outer_types.append(tname)
        # lambda
        out  = self.ident(xml) + 'auto describe_%s = [](dfproto::%s* proto, df::%s* dfhack) {\n' % (
            tname, rdr.outer_proto_tname(), rdr.outer_dfhack_tname()
        )
        out += '  proto->set_flags(dfhack->whole);\n'
        out += '};\n'
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

    def _convert_simple(self, names, deref=False, array=False, is_ptr=False):
        if is_ptr:
            sfield = '(*dfhack->%s)' % (names[1])
        else:
            sfield = 'dfhack->%s' % (names[1])
        out = 'proto->%s_%s(%s%s%s);\n' % (
            'add' if array else 'set', names[0],
            '*' if deref else '', sfield,
            '[i]' if array else ''
        )
        if deref:
            out = 'if (dfhack->%s%s != NULL) {\n' % (
                names[1], '[i]' if array else '') + out + '\n}\n'
        return out

    def _convert_field_compound(self, tname, names, deref=True, array=False):
        out = 'describe_%s(proto->%s_%s(), %sdfhack->%s%s);\n' % (
            tname,
            'add' if array else 'mutable', names[0],
            '' if deref else '&',
            names[1], '[i]' if array else ''
        )
        if deref:
            out = 'if (dfhack->%s%s != NULL) {\n' % (
                names[1], '[i]' if array else '') + out + '\n}\n'
        return out
    
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
            self.dfproto_imports.add(tname)
            return self.render_field_enum(xml)
        if subtype == 'df-linked-list':
            self.imports.add(tname)
        self.dfproto_imports.add(tname)
        self.imports.add(tname)
        return self.ident(xml, ctx.ident) + self._convert_field_compound(
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
            out = self.render_field(xml[0], ctx.set_deref(True).dec_ident())
            meta = xml[0].get(f'{self.ns}meta')
            if meta=='static-array' or meta=='container':
                # pointer to container
                out = 'if (dfhack->%s != NULL) {\n' % (
                    ctx.names[1]) + out + '\n}\n'
            return out
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
        if subtype == 'stl-bit-vector':
            return self.ident(xml) + '/* ignored stl-bit-vector container %s */\n' % (names[0])
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
                        # FIXME: handle ctx.deref
                        item_str = 'proto->add_%s_%s(%sdfhack->%s[i]->%s);' % (
                            names[0], v, '*' if deref else '', names[1], v
                        )
                if not item_str:
                    item_str = self._convert_field_compound(
                        tname, names, array=True
                    )
        else:
            meta = xml[0].get(f'{self.ns}meta')
            subtype = xml[0].get(f'{self.ns}subtype')
            tname = xml[0].get('type-name')
            if subtype == 'bitfield':
                out += self._convert_anon_bitfield(xml[0], names[0])
                tname = tname or 'T_'+names[0]
                item_str = self._convert_bitfield(tname, names, array=True)
            elif subtype == 'enum' or tname and tname.endswith('_type') or tname in self.exceptions_enum:
                if tname:
                    self.imports.add(tname)
                    self.dfproto_imports.add(tname)
                    ltname = tname
                else:
                    tname = 'T_' + names[0]
                    ltname = '%s_%s' % (self.outer_proto_tname(), tname)
                    out += self._convert_anon_enum(xml[0], names[0])
                item_str  = '  dfproto::%s value;\n' % (ltname)
                item_str += '  describe_%s(&value, &dfhack->%s[i]);\n' % (tname, names[0])
                item_str += '  proto->add_%s(value);\n' % (names[0])
            elif self.is_primitive_type(subtype):
                item_str = self._convert_simple(names, array=True, is_ptr=ctx.deref)
            else:
                if meta == 'pointer':
                    if len(xml[0]) == 0:
                        return self.ident(xml) + '/* ignored empty container %s */\n' % (names[0])
                    out += self._convert_anon_compound(xml[0][0], names[0])
                    item_str = self._convert_field_compound(
                        'T_'+names[0], names, array=True
                    )                    
                elif meta == 'compound':
                    out += self._convert_anon_compound(xml[0], names[0])
                    item_str = self._convert_field_compound(
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
                    item_str = self._convert_field_compound(
                        tname, names, array=True, deref=False
                    )
        
        if not item_str:
            item_str = self._convert_simple(
                names, deref, array=True, is_ptr=ctx.deref
            )
        count = xml.get('count')
        if not count:
            count = 'dfhack->%s%ssize()' % (names[1], '->' if ctx.deref else '.')
        out += self.ident(xml) + 'for (size_t i=0; i<%s; i++) {\n' % (count)
        out += self.ident(xml) + '  %s' % (item_str)
        out += self.ident(xml) + '}\n'
        return out
    
    
    # structs / classes

    def _render_struct_header(self, xml, tname, ctx):
        return self.ident(xml) + 'void %s::describe_%s(%s::%s* proto, df::%s* dfhack) {\n' % ( self.cpp_ns, tname, self.proto_ns, tname, tname )
    
    def _render_struct_footer(self, xml, ctx):
        return '}\n'
    
    def _render_struct_parent(self, xml, parent, ctx):
        self.dfproto_imports.add(parent)
        return self.ident(xml) + '  describe_%s(proto->mutable_parent(), dfhack);\n' % ( parent )

    def _render_struct_field(self, item, value, ctx):
        field = self.render_field(item, Context(value, ident=ctx.ident))
        if field.lstrip().startswith('/*'):
            field = ''
            value += 1
        return field, value

    def render_field_method(self, xml, ctx):
        method_name = xml.get('name')
        assert method_name.startswith('get')
        name = method_name[3:].lower()        
        tname = xml.get('ret-type')
        if self.is_primitive_type(tname):
            out  = self.ident(xml, ctx.ident) + ' '
            out += 'proto->set_%s(dfhack->%s());\n' % (name, method_name)
        else:
            self.imports.add(tname)
            self.dfproto_imports.add(tname)
            out  = 'df::%s df_%s = dfhack->%s();\n' % (tname, name, method_name)
            out += 'dfproto::%s %s;\n' % (tname, name)
            out += 'describe_%s(&%s, &df_%s);\n' % (tname, name, name)
            out += 'proto->set_%s(%s);\n' % (name, name)
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
            out += rdr.render_field(item)
        out += self.ident(xml) + '};\n'
        return out

    def render_field_compound(self, xml, ctx):
        subtype = xml.get(f'{self.ns}subtype')
        # if subtype == 'enum':
        #     return self.render_field_enum(xml)
        # if subtype == 'bitfield':
        #     return self.render_field_bitfield(xml)
        
        anon = xml.get(f'{self.ns}anon-compound')
        union = xml.get('is-union')
        if union == 'true':
            return self.render_field_union(xml)

        if not ctx.names:
            ctx.names = self.get_name(xml)
        tname = self.get_typedef_name(xml, ctx.names[0])
        if subtype == 'enum':
            out = self.copy()._convert_anon_enum(xml, ctx.names[0])
            out += self.ident(xml) + self._convert_enum(
                tname, ctx.names, anon=True
            )
        elif subtype == 'bitfield':
            out = self.copy()._convert_anon_bitfield(xml, ctx.names[0])
            out += self.ident(xml) + self._convert_bitfield(
                tname, ctx.names
            )
        else:
            out  = self.copy()._convert_anon_compound(xml, ctx.names[0])
            out += self.ident(xml) + self._convert_field_compound(
                tname, ctx.names, ctx.deref
            )
        return out
    

    # unions

    def render_field_union(self, xml):
        names = self.get_name(xml)
        if self.last_enum_descr == None:
            return '/* failed to find a discriminator for union %s */\n' % (self.get_typedef_name(xml, names[0]))
        tname = self.last_enum_descr.get('type-name')
        ename = self.get_name(self.last_enum_descr)[1]
        out  = '  switch (dfhack->%s) {\n' % (ename)
        for item in xml.findall(f'{self.ns}field'):
            iname = self.get_name(item)
            out += '    case ::df::enums::%s::%s:\n' % (tname, iname[1])
            out += '      proto->set_%s(dfhack->%s.%s);\n' % (iname[0], names[1], iname[1])
            out += '      break;\n'
        out += '    default:\n'
        out += '      proto->clear_%s();\n' % (names[0])
        out += '  }\n'
        return out


    # conversion of type
    
    def render_field_conversion(self, xml, ctx=None):
        names = self.get_name(xml)
        tname = self.get_typedef_name(xml, names[0])
        new_tname = xml.get('export-as')
        assert new_tname
        self.dfproto_imports.add('conversion')
        return self.ident(xml) + 'convert_%s_to_%s(&dfhack->%s, proto->mutable_%s());\n' % (
            tname, new_tname, names[0], names[0]
        )
    

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
    
