from collections import defaultdict
import sys
import traceback

from abstract_renderer import AbstractRenderer


class Context:
    
    def __init__(self, value=None, name=None, keyword=None, ident=None):
        self.value = value or 1
        self.name = name
        self.keyword = 'required' if keyword==None else keyword
        self.ident = ident or ''

    def set_keyword(self, kw):
        self.keyword = kw
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
        copy.imports = self.imports
        copy.version = self.version
        return copy

    def set_version(self, ver):
        self.version = ver
        return self

    def get_name(self, xml):
        # FIXME: properly handle exception RENAME
        return AbstractRenderer.get_name(self, xml)[0]


    # field or enum item
        
    def _render_line(self, xml, tname, value, name=None, keyword='required'):
        if self.version == 3 and keyword in ['required', 'optional']:
            keyword = ''        
        out = keyword + ' '
        if tname:
            out += tname + ' '
        if not name:
            name = self.get_name(xml)
        out += name + ' = ' + str(value) + ';'
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

    def render_enum(self, xml, value=1):
        name = self.get_name(xml)
        tname = self.get_typedef_name(xml, name)
        out = self.render_type_enum(xml, tname, prefix=name+'_', extra_ident='  ')
        out += self.ident(xml) + self._render_line(xml, tname, value, name) + '\n'
        return out

    
    # bitfields

    def render_masks(self, xml):
        out = self.ident(xml) + 'enum mask {\n'
        value = 0
        for item in xml.findall(f'{self.ns}field'):
            out += self.ident(xml) + '  %s = 0x%x;' % (
                self.get_name(item), value
            )
            out = self.append_comment(item, out) + '\n'
            value += 1
        out += self.ident(xml) + '}\n'
        return out
    
    def render_type_bitfield(self, xml, tname=None):
        if not tname:
            tname = xml.get('type-name')
        assert tname
        ident = self.ident(xml)
        out  = ident + 'message ' + tname + ' {\n'
        out += self.render_masks(xml)
        out += ident + '  required fixed32 flags = 1;'
        out  = self.append_comment(xml, out) + '\n'
        out += ident + '}\n'
        return out
    
    def render_bitfield(self, xml, value):
        name = self.get_name(xml)
        tname = self.get_typedef_name(xml, name)
        out  = self.copy().render_type_bitfield(xml, tname)
        out += self.ident(xml) + self._render_line(xml, tname, value, name) + '\n'
        return out

    
    # fields & containers

    def _convert_tname(self, tname):
        if ProtoRenderer.is_primitive_type(tname):
            tname = ProtoRenderer.convert_type(tname)
        elif tname:
            self.imports.add(tname)
        else:
            tname = 'bytes'
        return tname

    def render_simple_field(self, xml, ctx):
        tname = xml.get(f'{self.ns}subtype')
        if tname == 'enum' or tname == 'bitfield':
            tname = xml.get('type-name')
            self.imports.add(tname)
        else:
            tname = self._convert_tname(tname)
        return self._render_line(xml, tname, ctx.value, keyword=ctx.keyword)

    def render_pointer(self, xml, ctx):
        if ctx.keyword == 'required':
            ctx.keyword = 'optional'
        if not ctx.name:
            ctx.name = self.get_name(xml)
        tname = xml.get('type-name')
        if tname == None:
            if len(xml):
                return self.render_field(xml[0], ctx)
            else:
                return '// ignored pointer to unknown type\n'
        if ProtoRenderer.is_primitive_type(tname):
            tname = self.convert_type(tname)
            return self._render_line(xml, tname, ctx.value, ctx.name, ctx.keyword)
        # ref to complex type
        return self._render_line(xml, 'int32', ctx.value, name=ctx.name+'_ref', keyword=ctx.keyword)

    def render_container(self, xml, ctx):
        if not ctx.name:
            ctx.name = self.get_name(xml)
        if xml.get(f'{self.ns}subtype') == 'df-linked-list':
            return self.render_global(xml, ctx)
        tname = xml.get('pointer-type')
        if tname and not ProtoRenderer.is_primitive_type(tname):
            # convert to list of refs to avoid circular dependencies
            return self._render_line(xml, 'int32', ctx.value, ctx.name+'_ref', keyword='repeated')
        if not tname:
            tname = xml.get('type-name')
        if tname == 'pointer':
            # convert to list of refs to avoid circular dependencies
            tname = 'int32'
        if not tname and len(xml) > 0:
            # local anon compound
            tname = 'T_'+ctx.name
            if xml[0].get(f'{self.ns}meta') == 'pointer':
                out = self.render_pointer(xml[0], ctx.set_keyword('repeated'))
            else:
                tname = 'T_'+ctx.name
                out  = self.render_anon_compound(xml[0], tname)
                out += self.ident(xml[0]) + self._render_line(xml[0], tname, ctx.value, ctx.name, keyword='repeated')
            return out
        elif ProtoRenderer.is_primitive_type(tname):
            tname = self._convert_tname(tname)
            return self._render_line(xml, tname, ctx.value, ctx.name, keyword='repeated')
        elif len(xml):
            return self.render_field(xml[0], ctx)
        # container of unknown type
        return '  // ignored container %s\n' % (ctx.name)
            
    
    def render_global(self, xml, ctx):
        tname = xml.get('type-name')
        assert tname
        self.imports.add(tname)
        return self._render_line(xml, tname, ctx.value)
        
    
    # structs

    def render_struct_type(self, xml, tname=None, keyword='required'):
        if not tname:
            tname = xml.get('type-name')
        out  = self.ident(xml) + 'message ' + tname + ' {\n'
        parent = xml.get('inherits-from')
        value = 1
        if parent:
            out += self.ident(xml) + '  ' + self._render_line(xml, parent, 1, name='parent', keyword=keyword) + ' /* parent type */\n'
            self.imports.add(parent)
            value += 1        
        for item in xml.findall(f'{self.ns}field'):
            out += self.ident(item) + self.render_field(item, Context(value))
            if item.get('is-union'):
                value += len(item)
            else:
                value += 1
        out += self.ident(xml) + '}\n'
        return out

    def render_anon_compound(self, xml, tname=None):
        if not tname:
            tname = 'T_anon'
        return self.render_struct_type(xml, tname)

    def render_compound(self, xml, ctx):
        subtype = xml.get(f'{self.ns}subtype')
        if subtype == 'enum':
            return self.render_enum(xml, ctx.value)
        if subtype == 'bitfield':
            return self.render_bitfield(xml, ctx.value)
        
        anon = xml.get(f'{self.ns}anon-compound')
        union = xml.get('is-union')
        if union == 'true':
            if anon == 'true':
                return self.render_union(xml, 'anon', ctx.value)
            return self.render_union(xml, self.get_name(xml), ctx.value)
        if anon == 'true':
            return self.render_anon_compound(xml)

        if not ctx.name:
            ctx.name = self.get_name(xml)
        tname = self.get_typedef_name(xml, ctx.name)
        out  = self.copy().render_struct_type(xml, tname)
        out += self.ident(xml) + self._render_line(xml, tname, ctx.value, ctx.name, ctx.keyword) + '\n'
        return out
    

    # unions

    def render_union(self, xml, tname, value=1):
        fields = ''
        predecl = []
        for item in xml.findall(f'{self.ns}field'):
            meta = item.get(f'{self.ns}meta')
            if meta == 'compound':
                itname = 'T_anon_' + str(self.anon_id)
                self.anon_id += 1
                predecl += self.render_anon_compound(item, tname=itname)
                fields += self.ident(item) + '  ' + self._render_line(item, itname, value, keyword='')
            else:
                fields += self.ident(item) + self.render_simple_field(item, Context(value, keyword=''))
            value += 1
        out = ''
        for decl in predecl:
            out += decl
        out += 'oneof ' + tname + ' {\n'
        out += fields + self.ident(xml) + '}\n'
        return out
    

    # main renderer

    def render_field(self, xml, ctx=None):
        if not ctx:
            ctx = Context()
        comment = self.append_comment(xml, '') + '\n'
        return self.render_field_impl(xml, ctx, comment)

    def render_type(self, xml):
        if self.proto_ns:
            out = 'package ' + self.proto_ns + ';\n'
        else:
            out = ''
        out = self.append_comment(xml, out) + '\n'
        return out + self.render_type_impl(xml)
