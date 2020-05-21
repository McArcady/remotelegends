from collections import defaultdict
import sys
import traceback

from abstract_renderer import AbstractRenderer


class Context:
    
    def __init__(self, value=None, name=None, keyword=None, ident=None):
        self.value = value or 1
        self.name = name
        self.keyword = 'required' if keyword==None else keyword
        self.ident = ident or 0

    def set_value(self, value):
        self.value = value
        return self
    
    def set_name(self, name):
        self.name = name
        return self
    
    def set_keyword(self, kw):
        self.keyword = kw
        return self

    def dec_ident(self):
        self.ident -= 1
        return self

    def inc_ident(self):
        self.ident += 1
        return self
        

class ProtoRenderer(AbstractRenderer):

    def __init__(self, ns, proto_ns=None):
        AbstractRenderer.__init__(self, ns)
        # protobuf namespace
        self.proto_ns = proto_ns
        # external proto dependencies
        self.imports = set()
        # protobuf version (2|3)
        self.version = 2

    def copy(self):
        copy = ProtoRenderer(self.ns, proto_ns=self.proto_ns)
        AbstractRenderer.copy(self, copy)
        copy.imports = self.imports
        copy.version = self.version
        return copy

    def set_version(self, ver):
        self.version = ver
        return self

    def get_name(self, xml):
        # return protobuf name
        return AbstractRenderer.get_name(self, xml)[0]


    # field item
        
    def _render_line(self, xml, tname, ctx):
        if self.version == 3 and ctx.keyword in ['required', 'optional']:
            ctx.keyword = ''        
        out = self.ident(xml, ctx.ident) + ctx.keyword + ' '
        if tname:
            out += tname + ' '
        if not ctx.name:
            ctx.name = self.get_name(xml)
        out += ctx.name + ' = ' + str(ctx.value) + ';'
        return self.append_comment(xml, out) + '\n'

    
    # enumerations

    def _render_enum_item(self, xml, value, prefix=''):
        name = self.get_name(xml)
        out = prefix + name + ' = ' + str(value) + ';'
        return self.append_comment(xml, out) + '\n'

    def render_type_enum(self, xml, tname=None, prefix=None, extra_ident=''):
        if not tname:            
            tname = xml.get('type-name')
        assert tname
        out = self.ident(xml) + extra_ident + 'enum ' + tname + ' {\n'
        if prefix == None:
            prefix = tname + '_'
        value = 0
        postdecl = []
        for item in xml.findall('enum-item'):
            itemv = item.get('value')
            if itemv and int(itemv) < 0:
                postdecl.append(self._render_enum_item(item, int(itemv), prefix))
            else:
                if itemv and int(itemv) > value:
                    if value == 0:
                        out += self.ident(xml) + extra_ident + '  ' + prefix + 'ZERO = 0;\n'
                    value = int(itemv)
                out += self.ident(xml) + extra_ident + '  ' + self._render_enum_item(item, value, prefix)
                value += 1
        for line in postdecl:
            out += self.ident(xml) + extra_ident + '  ' + line
        out += self.ident(xml) + extra_ident + '}\n'
        return out

    def render_field_enum(self, xml, ctx):
        if not ctx.name:
            ctx.name = self.get_name(xml)
        tname = xml.get('type-name')
        if tname:
            if not self.is_primitive_type(tname):
                self.imports.add(tname)
            out = ''
        else:
            tname = self.get_typedef_name(xml, ctx.name)
            out = self.render_type_enum(xml, tname, prefix=tname+'_', extra_ident='  ')
        out += self._render_line(xml, tname, ctx) + '\n'
        return out

    
    # bitfields

    def _render_masks(self, xml):
        if len(xml) == 0:
            return '\n'
        out = self.ident(xml) + '  enum mask {\n'
        value = 0
        for item in xml.findall(f'{self.ns}field'):
            out += self.ident(item) + '  %s = 0x%x;' % (
                self.get_name(item), value
            )
            out = self.append_comment(item, out) + '\n'
            value += 1
        out += self.ident(xml) + '  }\n'
        return out
    
    def render_type_bitfield(self, xml, tname=None):
        if not tname:
            tname = xml.get('type-name')
        assert tname
        ident = self.ident(xml)
        out  = ident + 'message ' + tname + ' {\n'
        out += self._render_masks(xml)
        out += ident + '  required fixed32 flags = 1;'
        out  = self.append_comment(xml, out) + '\n'
        out += ident + '}\n'
        return out
    
    def render_field_bitfield(self, xml, ctx, tname=None):
        if not ctx.name:
            ctx.name = self.get_name(xml)
        if not tname:
            tname = self.get_typedef_name(xml, ctx.name)
        out  = self.copy().render_type_bitfield(xml, tname)
        out += self._render_line(xml, tname, ctx)
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
        tname = xml.get(f'{self.ns}subtype')
        if tname == 'enum' or tname == 'bitfield':
            tname = xml.get('type-name')
            self.imports.add(tname)
        else:
            tname = self._convert_tname(tname)
        return self._render_line(xml, tname, ctx)
    
    def render_field_global(self, xml, ctx):
        tname = xml.get('type-name')
        assert tname
        self.imports.add(tname)
        return self._render_line(xml, tname, ctx)


    # pointers and containers
    
    def render_field_pointer(self, xml, ctx):
        if ctx.keyword == 'required':
            ctx.keyword = 'optional'
        if not ctx.name:
            ctx.name = self.get_name(xml)
        ctx.dec_ident()            
        tname = xml.get('type-name')
        if tname == None:
            if len(xml):
                return self.render_field(xml[0], ctx)
            else:
                return self.ident(xml) + '/* ignored pointer to unknown type */\n'
        if self.is_primitive_type(tname):
            tname = self.convert_type(tname)
            return self._render_line(xml, tname, ctx)
        # replace type with an id ?
        for k,v in iter(self.exceptions_index):
            if k == tname:
                key = '_'+v
                return self._render_line(xml, 'int32', ctx.set_name(ctx.name+key))
        return self.render_field(xml[0], ctx)

    def render_field_container(self, xml, ctx):
        if not ctx.name:
            ctx.name = self.get_name(xml)
        if xml.get(f'{self.ns}subtype') == 'df-linked-list':
            return self.render_field_global(xml, ctx)
        tname = xml.get('pointer-type')
        if tname and not self.is_primitive_type(tname):
            return self.render_field_pointer(xml[0], ctx.set_keyword('repeated'))            
        if not tname:
            tname = xml.get('type-name')
        if tname == 'pointer':
            # convert to list of refs to avoid circular dependencies
            tname = 'int32'
        if not tname and len(xml) > 0:
            tname = 'T_'+ctx.name
            subtype = xml[0].get(f'{self.ns}subtype')
            meta = xml[0].get(f'{self.ns}meta')
            if meta == 'pointer':
                out = self.render_field_pointer(xml[0], ctx.set_keyword('repeated'))
            elif meta=='container' or meta=='static-array':
                return '/* ignored container of containers %s */\n' % (ctx.name)
            elif subtype == 'bitfield':
                # local anon bitfield
                tname = 'T_'+ctx.name
                out = self.render_field_bitfield(xml[0], ctx.set_keyword('repeated'), tname)
            elif subtype == 'enum':
                out = self.render_field_enum(xml[0], ctx.set_keyword('repeated'))
            elif self.is_primitive_type(subtype):
                tname = self.convert_type(subtype)
                out = self._render_line(xml[0], tname, ctx.set_keyword('repeated'))
            elif xml[0].get('type-name'):
                tname = xml[0].get('type-name')
                self.imports.add(tname)
                out = self._render_line(xml[0], tname, ctx.set_keyword('repeated'))
            else:
                # local anon compound
                tname = 'T_'+ctx.name
                out  = self.render_type_struct(xml[0], tname, ctx)
                out += self._render_line(xml[0], tname, ctx.set_keyword('repeated'))
            return out
        elif self.is_primitive_type(tname):
            tname = self._convert_tname(tname)
            return self._render_line(xml, tname, ctx.set_keyword('repeated'))
        elif len(xml):
            return self.render_field(xml[0], ctx.set_keyword('repeated'))
        # container of unknown type
        return '  /* ignored container %s */\n' % (ctx.name)
        
    
    # structs

    def render_type_struct(self, xml, tname=None, ctx=None):
        if not ctx:
            ctx = Context()
        if not tname:
            tname = xml.get('type-name')
        out  = self.ident(xml, ctx.ident) + 'message ' + tname + ' {\n'
        parent = xml.get('inherits-from')
        value = 1
        if parent:
            out += self.ident(xml, ctx.ident+1) + '/* parent type */\n'
            out += self._render_line(xml, parent, ctx.set_name('parent').inc_ident())
            self.imports.add(parent)
            value += 1        
        for item in xml.findall(f'{self.ns}field'):
            field = self.render_field(item, Context(value, ident=ctx.ident))
            out += field
            if field.lstrip().startswith('/*'):
                continue
            if item.get('is-union'):
                value += len(item)
            else:
                value += 1
        out += self.ident(xml, ctx.ident) + '}\n'
        return out

    def render_field_compound(self, xml, ctx):
        subtype = xml.get(f'{self.ns}subtype')
        if subtype == 'enum':
            return self.render_field_enum(xml, ctx)
        if subtype == 'bitfield':
            return self.render_field_bitfield(xml, ctx)
        
        anon = xml.get(f'{self.ns}anon-compound')
        union = xml.get('is-union')
        if union == 'true':
            if anon == 'true':
                return self.render_field_union(xml, 'anon', ctx.value)
            return self.render_field_union(xml, self.get_name(xml), ctx.value)
        if anon == 'true':
            return self.render_type_struct(xml, 'T_anon', ctx)

        if not ctx.name:
            ctx.name = self.get_name(xml)
        tname = self.get_typedef_name(xml, ctx.name)
        out  = self.copy().render_type_struct(xml, tname)
        out += self._render_line(xml, tname, ctx)
        return out
    

    # unions

    def render_field_union(self, xml, tname, value=1):
        fields = ''
        predecl = []
        for item in xml.findall(f'{self.ns}field'):
            ctx = Context(value, keyword='')
            meta = item.get(f'{self.ns}meta')
            if meta == 'compound':
                itname = self.get_type_name(item)
                predecl += self.render_type_struct(item, tname=itname, ctx=ctx)
                fields += self._render_line(item, itname, ctx)
            else:
                fields += self.render_field_simple(item, ctx)
            value += 1
        out = ''
        for decl in predecl:
            out += decl
        out += self.ident(xml) + 'oneof ' + tname + ' {\n'
        out += fields
        out += self.ident(xml) + '}\n'
        return out
    

    # main renderer

    def render_field(self, xml, ctx=None):
        if not ctx:
            ctx = Context()
        field = self.render_field_impl(xml, ctx)
        if not field.rstrip().endswith('*/'):
            comment = self.append_comment(xml, '')
            return self.ident(xml, ctx.ident) + '%s\r%s' % (comment, field)
        return field

    def render_type(self, xml):
        if self.proto_ns:
            out = 'package ' + self.proto_ns + ';\n'
        else:
            out = ''
        out = self.append_comment(xml, out) + '\n'
        return out + self.render_type_impl(xml)
