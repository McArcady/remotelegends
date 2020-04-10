from collections import defaultdict
import sys
import traceback


class Renderer:

    def __init__(self, namespace):
        self.ns = namespace
        self.imports = []
    
    TYPES = defaultdict(lambda: None, {
        k:v for k,v in {
        'int8_t': 'int32',
        'int16_t': 'int32',
        'int32_t': 'int32',
        'stl-string': 'string',
        }.items()})

    @staticmethod
    def convert_type(typ):
        return Renderer.TYPES[typ]

    @staticmethod
    def is_primitive_type(typ):
        return typ in Renderer.TYPES.keys()

    
    # enumerations

    def render_enum_type(self, xml, tname=None):
        if not tname:            
            tname = xml.get('type-name')
        assert tname
        out = 'enum ' + tname + ' {\n'
        count = 0
        ident = '  '
        for item in xml.findall('enum-item'):
            name = item.get('name')
            assert name
            out += ident + name + ' = ' + str(count) + ';\n'
            count += 1
        out += '}\n'
        return out

    def render_enum(self, xml, value=1):
        tname = xml.get(f'{self.ns}typedef-name')
        name = xml.get('name')
        assert tname
        assert name
        out = self.render_enum_type(xml, tname)
        out += tname + ' ' + name + ' = ' + str(value) + ';\n'
        return out

    def render_global_enum(self, xml, value=1):
        tname = xml.get('type-name')
        name = xml.get('name')
        assert tname
        assert name
        self.imports.append(tname)
        out = tname + ' ' + name + ' = ' + str(value) + ';\n'
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
        name = xml.get('name')
        assert name
        assert tname
        out = 'repeated ' + tname + ' ' + name + ' = ' + str(value) + ';\n'
        return out

    def render_simple_field(self, xml, value=1):
        styp = xml.get(f'{self.ns}subtype')
        if Renderer.is_primitive_type(styp):
            styp = Renderer.convert_type(styp)
        if not styp:
            styp = 'T_anon'
        name = xml.get('name')
        if not name:
            name = xml.get(f'{self.ns}anon-name')
        if not name:
            name = 'anon'
        return styp + ' ' + name + ' = ' + str(value) + ';\n'

    def render_field(self, xml, value):
        meta = xml.get(f'{self.ns}meta')
        assert meta
        if meta != 'primitive' and meta != 'number':
            return self.render(xml, value)
        else:
            return self.render_simple_field(xml, value)

    def render_pointer(self, xml, value=1):
        tname = xml.get('type-name')
        if not tname:
            tname = 'bytes'
        name = xml.get('name')
        if not name:
            name = xml.get(f'{self.ns}anon-name')
        assert name
        assert tname
        if not Renderer.is_primitive_type(tname):
            self.imports.append(tname)
        out = tname + ' ' + name + ' = ' + str(value) + ';\n'
        return out

    
    # structs

    def render_struct_type(self, xml, tname=None):
        if not tname:
            tname = xml.get('type-name')
        out  = 'message ' + tname + ' {\n'
        count = 1
        ident = '  '
        for item in xml.findall(f'{self.ns}field'):
            out += ident + self.render_field(item, count)
            count += 1
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
        
        anon = xml.get(f'{self.ns}anon-compound')
        if anon == 'true':
            union = xml.get('is-union')
            if union == 'true':
                return self.render_union(xml, 'anon')
            return self.render_anon_compound(xml)
        
        tname = xml.get(f'{self.ns}typedef-name')
        if tname:
            name = xml.get('name')
            assert name
            out = self.render_struct_type(xml, tname)
            out += tname + ' ' + name + ' = ' + str(value) + ';\n'
            return out

        raise Exception('not supported: '+meta+'/'+subtype)
        

    # unions

    def render_union(self, xml, tname):
        count = 1
        ident = '  '
        fields = ''
        predecl = []
        for item in xml.findall(f'{self.ns}field'):
            meta = item.get(f'{self.ns}meta')
            if meta == 'compound':
                predecl += self.render_anon_compound(item)
            fields += ident + self.render_simple_field(item, count)
            count += 1
        out = ''
        if predecl:
            for decl in predecl:
                out += decl
        out += 'oneof ' + tname + ' {\n'
        out += fields + '}'
        return out
    

    # main renderer

    def render(self, xml, value=1):
        try:
            meta = xml.get(f'{self.ns}meta')
            if meta == 'compound':
                return self.render_compound(xml, value)
            elif meta == 'container':
                return self.render_container(xml, value)
            elif meta == 'enum-type':
                return self.render_enum_type(xml)
            elif meta == 'global':
                return self.render_global_enum(xml)
            elif meta == 'pointer':
                return self.render_pointer(xml)
            elif meta == 'struct-type':
                return self.render_struct_type(xml)
        except Exception as e:
            _,value,tb = sys.exc_info()
            print('error rendering element %s (meta=%s) at line %d:' % (xml.tag, meta, xml.sourceline))
            traceback.print_tb(tb)
            return ""
        raise Exception('no supported: element '+xml.tag+': meta='+str(meta))
