from collections import defaultdict
import sys
import traceback


class Renderer:

    def __init__(self, namespace):
        self.ns = '{'+namespace+'}'
        self.imports = []
    
    TYPES = defaultdict(lambda: None, {
        k:v for k,v in {
        'int8_t': 'int32',
        'int16_t': 'int32',
        'int32_t': 'int32',
        'stl-string': 'string',
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
        if not name:
            name = 'anon_' + str(value)
        return name

    def ident(self, xml):
        ident = xml.get(f'{self.ns}level') or 1
        return '  ' * int(ident)
        
    
    # enumerations

    def render_enum_type(self, xml, tname=None, itype='enum-item', extra_ident=''):
        if not tname:            
            tname = xml.get('type-name')
        assert tname
        out = self.ident(xml) + extra_ident + 'enum ' + tname + ' {\n'
        value = 0
        for item in xml.findall(itype):
            name = self.get_name(item, value)
            assert name
            out += self.ident(item) + extra_ident + name + ' = ' + str(value) + ';'
            comment = item.get('comment')
            if comment:
                out += ' /* ' + comment + '*/'
            out += '\n'
            value += 1
        out += self.ident(xml) + extra_ident + '}\n'
        return out

    def render_enum(self, xml, value=1):
        tname = xml.get(f'{self.ns}typedef-name')
        name = self.get_name(xml, value)
        assert tname
        assert name
        out = self.render_enum_type(xml, tname)
        out += self.ident(xml) + tname + ' ' + name + ' = ' + str(value) + ';\n'
        return out

    
    # fields & containers
    
    def render_container(self, xml, value=1):
        tname = xml.get('pointer-type')
        if tname:
            self.imports.append(tname)
        else:
            tname = Renderer.convert_type(xml.get('type-name'))
        if not tname:
            tname = 'bytes'
        name = self.get_name(xml, value)
        out = 'repeated ' + tname + ' ' + name + ' = ' + str(value) + ';\n'
        return out

    def render_simple_field(self, xml, value=1):
        styp = xml.get(f'{self.ns}subtype')
        if Renderer.is_primitive_type(styp):
            styp = Renderer.convert_type(styp)
        if not styp:
            styp = 'T_anon'
        name = self.get_name(xml, value)
        return styp + ' ' + name + ' = ' + str(value) + ';\n'

    def render_pointer(self, xml, value=1):
        tname = xml.get('type-name')
        if not tname:
            tname = 'bytes'
        name = self.get_name(xml, value)
        if not Renderer.is_primitive_type(tname):
            self.imports.append(tname)
        out = tname + ' ' + name + ' = ' + str(value) + ';\n'
        return out

    def render_global(self, xml, value=1):
        tname = xml.get('type-name')
        assert tname
        name = self.get_name(xml, value)
        self.imports.append(tname)
        out = tname + ' ' + name + ' = ' + str(value) + ';\n'
        return out

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
        value = 1
        for item in xml.findall(f'{self.ns}field'):
            out += self.ident(item) + self.render_field(item, value)
            value += 1
        out += '}\n'
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
            return self.render_union(xml, self.get_name(xml), value)
        if anon == 'true':
            return self.render_anon_compound(xml)
        
        tname = xml.get(f'{self.ns}typedef-name')
        if tname:
            name = self.get_name(xml, value)
            out = self.render_struct_type(xml, tname)
            out += tname + ' ' + name + ' = ' + str(value) + ';\n'
            return out

        raise Exception('not supported: '+meta+'/'+subtype)
    

    # unions

    def render_union(self, xml, tname, value=1):
        fields = ''
        predecl = []
        for item in xml.findall(f'{self.ns}field'):
            meta = item.get(f'{self.ns}meta')
            if meta == 'compound':
                predecl += self.render_anon_compound(item)
            fields += self.ident(item) + self.render_simple_field(item, value)
            value += 1
        out = ''
        if predecl:
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
        out += self.render_enum_type(xml, 'mask', itype=f'{self.ns}field', extra_ident='  ')
        out += ident + '  ' + 'fixed32 flags = 1;\n'
        out += ident + '}\n'
        return out
    
    def render_bitfield(self, xml, value):
        tname = xml.get(f'{self.ns}typedef-name')
        assert tname
        name = self.get_name(xml, value)
        out  = self.render_bitfield_type(xml, tname)
        out += self.ident(xml) + tname + ' ' + name + ' = ' + str(value) + ';\n'
        return out
        

    # main renderer

    def render(self, xml, value=1):
        # TODO: handle comments for all types
        try:
            meta = xml.get(f'{self.ns}meta')
            if not meta:
                return '// ignored global-object: %s' % (xml.get('name'));
            elif meta == 'bitfield-type':
                return self.render_bitfield_type(xml)
            elif meta == 'class-type':
                return '// ignored class-type: %s' % (xml.get('type-name'));
            elif meta == 'compound':
                return self.render_compound(xml, value)
            elif meta == 'container':
                return self.render_container(xml, value)
            elif meta == 'enum-type':
                return self.render_enum_type(xml)
            elif meta == 'global':
                return self.render_global(xml)
            elif meta == 'pointer':
                return self.render_pointer(xml)
            elif meta == 'static-array':
                return self.render_container(xml, value)
            elif meta == 'struct-type':
                return self.render_struct_type(xml)
        except Exception as e:
            _,value,tb = sys.exc_info()
            print('error rendering element %s (meta=%s) at line %d: %s' % (xml.tag, meta if meta else '<unknown>', xml.sourceline, e))
            traceback.print_tb(tb)
            return ""
        raise Exception('not supported: element '+xml.tag+': meta='+str(meta))
