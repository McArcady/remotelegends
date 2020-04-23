from collections import defaultdict
import sys
import traceback


class ProtoRenderer:

    def __init__(self, ns, proto_ns=None):
        self.ns = '{'+ns+'}'
        self.proto_ns = proto_ns
        self.imports = set()
        self.version = 2
        self.exceptions = []
    
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

    def set_version(self, ver):
        self.version = ver
        return self

    def add_exception_rename(self, path, new_name):
        self.exceptions.append((path, new_name))
        return self

    @staticmethod
    def convert_type(typ):
        return ProtoRenderer.TYPES[typ]

    @staticmethod
    def is_primitive_type(typ):
        return typ in ProtoRenderer.TYPES.keys()

    def get_name(self, xml, value=1):
        name = xml.get('name')
        for k,v in iter(self.exceptions):
            found = xml.getroottree().xpath(k, namespaces={'ld': self.ns[1:-1]})
            if found and found[0] is xml:
                name = v
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

    def append_comment(self, xml, line):
        comment = xml.get('comment')
        if comment:
            return line + ' /* ' + comment + ' */'
        return line
        
    def _render_line(self, xml, tname, value, name=None, keyword='required'):
        if self.version == 3 and keyword in ['required', 'optional']:
            keyword = ''        
        out = keyword + ' '
        if tname:
            out += tname + ' '
        if not name:
            name = self.get_name(xml, value)
        out += name + ' = ' + str(value) + ';'
        return self.append_comment(xml, out) + '\n'

    
    # enumerations

    def _render_enum_item(self, xml, tname, value, prefix=''):
        name = self.get_name(xml, value)
        out = prefix + name + ' = ' + str(value) + ';'
        return self.append_comment(xml, out) + '\n'

    def render_enum_type(self, xml, tname=None, prefix=None, extra_ident=''):
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
                postdecl.append(self._render_enum_item(item, tname, int(itemv), prefix))
            else:
                if itemv and int(itemv) > value:
                    if value == 0:
                        out += self.ident(xml) + extra_ident + '  ' + prefix + 'ZERO = 0;\n'
                    value = int(itemv)
                out += self.ident(xml) + extra_ident + '  ' + self._render_enum_item(item, tname, value, prefix)
                value += 1
        for line in postdecl:
            out += self.ident(xml) + extra_ident + '  ' + line
        out += self.ident(xml) + extra_ident + '}\n'
        return out

    def render_enum(self, xml, value=1):
        name = self.get_name(xml, value)
        tname = self.get_typedef_name(xml, name)
        out = self.render_enum_type(xml, tname, prefix=name+'_', extra_ident='  ')
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

    def render_simple_field(self, xml, value=1, keyword='required'):
        tname = xml.get(f'{self.ns}subtype')
        if tname == 'enum' or tname == 'bitfield':
            tname = xml.get('type-name')
            self.imports.add(tname)
        else:
            tname = self._convert_tname(tname)
        name = self.get_name(xml, value)
        return self._render_line(xml, tname, value, keyword=keyword)

    def render_pointer(self, xml, value=1, name=None):
        if not name:
            name = self.get_name(xml, value)
        tname = xml.get('type-name')
        if tname == None and len(xml):
            return self.render_field(xml[0], value, name)
        return self._render_line(xml, 'int32', value, name=name+'_ref', keyword='optional')

    def render_container(self, xml, value=1, name=None):
        if not name:
            name = self.get_name(xml)
        if xml.get(f'{self.ns}subtype') == 'df-linked-list':
            return self.render_global(xml, value)
        tname = xml.get('pointer-type')
        if tname and not ProtoRenderer.is_primitive_type(tname):
            return self.render_pointer(xml, value)
        if not tname:
            tname = xml.get('type-name')
        if tname == 'pointer':
            tname = 'int32'
        elif ProtoRenderer.is_primitive_type(tname):
            tname = self._convert_tname(tname)
            return self._render_line(xml, tname, value, name, keyword='repeated')
        elif len(xml):
            return self.render_field(xml[0], value, name)
        # container of unknown type
        return '  // ignored container %s' % (name)
            
    
    def render_global(self, xml, value=1):
        tname = xml.get('type-name')
        assert tname
        self.imports.add(tname)
        return self._render_line(xml, tname, value)
        
    
    # structs

    def render_struct_type(self, xml, tname=None):
        if not tname:
            tname = xml.get('type-name')
        out  = self.ident(xml) + 'message ' + tname + ' {\n'
        parent = xml.get('inherits-from')
        value = 1
        if parent:
            out += self.ident(xml) + '  ' + self._render_line(xml, parent, 1, name='parent') + ' /* parent type */\n'
            self.imports.add(parent)
            value += 1        
        for item in xml.findall(f'{self.ns}field'):
            out += self.ident(item) + self.render_field(item, value)
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
            return self.render_union(xml, self.get_name(xml,value), value)
        if anon == 'true':
            return self.render_anon_compound(xml)

        if not name:
            name = self.get_name(xml, value)
        tname = self.get_typedef_name(xml, name)
        out = self.render_struct_type(xml, tname)
        out += self.ident(xml) + self._render_line(xml, tname, value, name) + '\n'
        return out
    

    # unions

    def render_union(self, xml, tname, value=1):
        fields = ''
        predecl = []
        for item in xml.findall(f'{self.ns}field'):
            meta = item.get(f'{self.ns}meta')
            if meta == 'compound':
                itname = 'T_anon_'+str(value)
                predecl += self.render_anon_compound(item, tname=itname)
                fields += self.ident(item) + '  ' + self._render_line(item, itname, value, keyword='')
            else:
                fields += self.ident(item) + self.render_simple_field(item, value, keyword='')
            value += 1
        out = ''
        for decl in predecl:
            out += decl
        out += 'oneof ' + tname + ' {\n'
        out += fields + self.ident(xml) + '}\n'
        return out

    
    # bitfields

    def render_bitfield_masks(self, xml):
        out = self.ident(xml) + 'enum mask {\n'
        value = 0
        for item in xml.findall(f'{self.ns}field'):
            out += self.ident(xml) + '  %s = 0x%x;' % (
                self.get_name(item,value), value
            )
            out = self.append_comment(item, out) + '\n'
            value += 1
        out += self.ident(xml) + '}\n'
        return out
    
    def render_bitfield_type(self, xml, tname=None):
        if not tname:
            tname = xml.get('type-name')
        assert tname
        ident = self.ident(xml)
        out  = ident + 'message ' + tname + ' {\n'
        out += self.render_bitfield_masks(xml)
        out += ident + '  ' + self._render_line(xml, 'fixed32', 1, name='flags') + '\n'
        out += ident + '}\n'
        return out
    
    def render_bitfield(self, xml, value):
        name = self.get_name(xml, value)
        tname = self.get_typedef_name(xml, name)
        out  = self.render_bitfield_type(xml, tname)
        out += self.ident(xml) + self._render_line(xml, tname, value, name) + '\n'
        return out
    

    # main renderer

    def render_field(self, xml, value=1, name=None):
        # TODO: handle comments for all types
        meta = xml.get(f'{self.ns}meta')
        if not meta or meta == 'compound':
            return self.render_compound(xml, value, name)
        if meta == 'primitive' or meta == 'number' or meta == 'bytes':
            return self.render_simple_field(xml, value)
        elif meta == 'container' or meta == 'static-array':
            return self.render_container(xml, value, name)
        elif meta == 'global':
            return self.render_global(xml, value)
        elif meta == 'pointer':
            return self.render_pointer(xml, value, name)
        raise Exception('not supported: '+xml.tag+': meta='+str(meta))

    def render_type(self, xml):
        meta = xml.get(f'{self.ns}meta')
        if self.proto_ns:
            out = 'package ' + self.proto_ns + ';\n'
        else:
            out = ''
        out = self.append_comment(xml, out) + '\n'
        if meta == 'bitfield-type':
            return out + self.render_bitfield_type(xml)
        elif meta == 'enum-type':
            return out + self.render_enum_type(xml)
        elif meta == 'class-type':
            return out + self.render_struct_type(xml)
        elif meta == 'struct-type':
            return out + self.render_struct_type(xml)
        raise Exception('not supported: '+xml.tag+': meta='+str(meta))
