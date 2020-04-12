from collections import defaultdict
import sys
import traceback


class Renderer:

    def __init__(self, namespace):
        self.ns = '{'+namespace+'}'
        self.imports = set()
    
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
            'stl-fstream': 'bytes',
            'static-string': 'string',
            'ptr-string': 'string',
            'padding': 'bytes',
        }.items()})

    @staticmethod
    def convert_type(typ):
        return Renderer.TYPES[typ]

    @staticmethod
    def is_primitive_type(typ):
        return typ in Renderer.TYPES.keys()

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

    def render_enum_type(self, xml, tname=None, itype='enum-item', prefix=None, extra_ident=''):
        if not tname:            
            tname = xml.get('type-name')
        assert tname
        out = self.ident(xml) + extra_ident + 'enum ' + tname + ' {\n'
        if prefix == None:
            prefix = tname + '_'
        value = 0
        postdecl = []
        for item in xml.findall(itype):
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
        out += self.ident(xml) + tname + ' ' + name + ' = ' + str(value) + ';\n'
        return out

    
    # fields & containers

    def _convert_tname(self, tname):
        if Renderer.is_primitive_type(tname):
            tname = Renderer.convert_type(tname)
        elif tname:
            self.imports.add(tname)
        else:
            tname = 'bytes'
        return tname

    def render_simple_field(self, xml, value=1):
        tname = xml.get(f'{self.ns}subtype')
        if tname == 'enum' or tname == 'bitfield':
            tname = xml.get('type-name')
            self.imports.add(tname)
        else:
            tname = self._convert_tname(tname)
        name = self.get_name(xml, value)
        return self._render_line(xml, tname, value)

    def render_pointer(self, xml, value=1):
        tname = xml.get('type-name')
        if not tname:
            tname = 'bytes'
        return self._render_line(xml, 'int32', value, name=self.get_name(xml,value)+'_ref')

    def render_container(self, xml, value=1):
        tname = xml.get('pointer-type')
        if tname and not Renderer.is_primitive_type(tname):
            return 'repeated '+ self.render_pointer(xml, value)
        if not tname:
            tname = xml.get('type-name')
        if tname == 'pointer':
            tname = 'int32'
        else:
            tname = self._convert_tname(tname)
        return self._render_line(xml, 'repeated '+tname, value)
    
    def render_global(self, xml, value=1):
        tname = xml.get('type-name')
        assert tname
        self.imports.add(tname)
        return self._render_line(xml, tname, value)

    def render_field(self, xml, value):
        meta = xml.get(f'{self.ns}meta')
        assert meta
        if meta == 'primitive' or meta == 'number' or meta == 'bytes':
            return self.render_simple_field(xml, value)
        else:
            return self.render(xml, value)
        
    
    # structs

    def render_struct_type(self, xml, tname=None):
        if not tname:
            tname = xml.get('type-name')
        out  = self.ident(xml) + 'message ' + tname + ' {\n'
        parent = xml.get('inherits-from')
        value = 1
        if parent:
            out += self.ident(xml) + '  ' + parent + ' parent = 1; /* parent type */\n'
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

    def render_compound(self, xml, value=1):
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
        
        name = self.get_name(xml, value)
        tname = self.get_typedef_name(xml, name)
        out = self.render_struct_type(xml, tname)
        out += self.ident(xml) + tname + ' ' + name + ' = ' + str(value) + ';\n'
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
                fields += self.ident(item) + '  ' + self._render_line(item, itname, value)
            else:
                fields += self.ident(item) + self.render_simple_field(item, value)
            value += 1
        out = ''
        for decl in predecl:
            out += decl
        out += 'oneof ' + tname + ' {\n'
        out += fields + self.ident(xml) + '}\n'
        return out

    
    # bitfields
    
    def render_bitfield_type(self, xml, tname=None):
        if not tname:
            tname = xml.get('type-name')
        assert tname
        ident = self.ident(xml)
        out  = ident + 'message ' + tname + ' {\n'
        # FIXME: values of enum shall be bit-masks
        out += self.render_enum_type(xml, 'mask', itype=f'{self.ns}field', extra_ident='  ', prefix='')
        out += ident + '  ' + 'fixed32 flags = 1;\n'
        out += ident + '}\n'
        return out
    
    def render_bitfield(self, xml, value):
        name = self.get_name(xml, value)
        tname = self.get_typedef_name(xml, name)
        out  = self.render_bitfield_type(xml, tname)
        out += self.ident(xml) + tname + ' ' + name + ' = ' + str(value) + ';\n'
        return out
        

    # main renderer

    def render(self, xml, value=1):
        # TODO: handle comments for all types
        try:
            meta = xml.get(f'{self.ns}meta')
            if not meta or meta == 'compound':
                return self.render_compound(xml, value)
            elif meta == 'container':
                return self.render_container(xml, value)
            elif meta == 'global':
                return self.render_global(xml, value)
            elif meta == 'pointer':
                return self.render_pointer(xml, value)
            elif meta == 'static-array':
                return self.render_container(xml, value)
            
            else:
                if meta == 'bitfield-type':
                    return self.render_bitfield_type(xml)
                elif meta == 'enum-type':
                    return self.render_enum_type(xml)
                elif meta == 'class-type':
                    return self.render_struct_type(xml)
                elif meta == 'struct-type':
                    return self.render_struct_type(xml)
            
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
        raise Exception('not supported: element '+xml.tag+': meta='+str(meta))
