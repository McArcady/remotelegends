from collections import defaultdict


class Renderer:

    def __init__(self):
        pass
    
    TYPES = defaultdict(lambda: None, {
        k:v for k,v in {
        'int8_t': 'int32',
        'int16_t': 'int32',
        'int32_t': 'int32',
        'stl-string': 'string',
        }.items()})

    @staticmethod
    def convert_type(typ):
        return Renderer.TYPES[typ] or 'T_'+typ

    # enumerations

    def render_enum_type(self, xml, tname=None):
        if not tname:            
            tname = xml.get('type-name')
        out = 'enum ' + tname + ' {\n'
        count = 0
        ident = '  '
        for item in xml.findall('enum-item'):
            out += ident + item.get('name') + ' = ' + str(count) + ';\n'
            count += 1
        out += '}\n'
        return out

    def render_enum(self, xml, value=1):
        tname = xml.get('{ns}typedef-name')
        name = xml.get('name')
        out = self.render_enum_type(xml, tname)
        out += tname + ' ' + name + ' = ' + str(value) + ';\n'
        return out

    # fields & containers
    
    def render_container(self, xml):
        tname = xml.get('type-name')
        name = xml.get('name')
        out = 'repeat ' + Renderer.convert_type(tname) + ' ' + name + ';\n'
        return out

    def render_field(self, xml, value):
        styp = Renderer.convert_type(xml.get('{ns}subtype') or 'anon')
        name = xml.get('name') or 'anon'
        return styp + ' ' + name + ' = ' + str(value) + ';\n'

    # structs

    def render_struct_type(self, xml, tname=None):
        if not tname:
            tname = xml.get('type-name')
        out  = 'message ' + tname + ' {\n'
        count = 1
        ident = '  '
        for item in xml.findall('{ns}field'):
            out += ident + self.render_field(item, count)
            count += 1
        out += '}\n'
        return out

    def render_anon_compound(self, xml, tname=None):
        if not tname:
            tname = 'T_anon'
        return self.render_struct_type(xml, tname)

    # unions

    def render_union(self, xml, tname):
        count = 1
        ident = '  '
        fields = ''
        predecl = []
        for item in xml.findall('{ns}field'):
            meta = item.get('{ns}meta')
            if meta == 'compound':
                predecl += self.render_anon_compound(item)
            fields += ident + self.render_field(item, count)
            count += 1
        out = ''
        if predecl:
            for decl in predecl:
                out += decl
            out += '\n'
        out += 'oneof ' + tname + ' {\n'
        out += fields + '}'
        return out

    # main renderer

    def render(self, xml):
        meta = xml.get('{ns}meta')
        if meta == 'enum-type':
            return self.render_enum_type(xml)
        elif meta == 'compound':
            subtype = xml.get('{ns}subtype')
            anon = xml.get('{ns}anon-compound')
            union = xml.get('is-union')
            if subtype == 'enum':
                return self.render_enum(xml)
            elif anon == 'true':
                if union == 'true':
                    return self.render_union(xml, 'anon')
                return self.render_anon_compound(xml)
            else:
                raise Exception('not supported: '+meta+'/'+subtype)
        elif meta == 'container':
            return self.render_container(xml)
        elif meta == 'struct-type':
            return self.render_struct_type(xml)
        else:
            raise Exception('no supported: '+meta)
