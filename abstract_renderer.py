from collections import defaultdict


class AbstractRenderer:

    def __init__(self, xml_ns):
        # xml namespaces
        if not xml_ns.startswith('{'):
            self.ns = '{'+xml_ns+'}'
        else:
            self.ns = xml_ns        
        # cache and id of last anon field
        self.anon_xml = None
        self.anon_id = 0
        # rules for special elements
        self.exceptions_rename = []
        self.exceptions_ignore = []
        self.exceptions_index = []

    def copy(self, target):
        target.exceptions_ignore = self.exceptions_ignore
        target.exceptions_rename = self.exceptions_rename
        target.exceptions_index = self.exceptions_index

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

    @staticmethod
    def convert_type(typ):
        return AbstractRenderer.TYPES[typ]

    @staticmethod
    def is_primitive_type(typ):
        return typ in AbstractRenderer.TYPES.keys()

    def add_exception_rename(self, xpath, new_name):
        self.exceptions_rename.append((xpath, new_name))
        return self

    def add_exception_ignore(self, xpath):
        self.exceptions_ignore.append(xpath)
        return self

    def add_exception_index(self, tname, field):
        self.exceptions_index.append((tname, field))
        return self

    def ident(self, xml):
        ident = xml.get(f'{self.ns}level') or 1
        return '  ' * int(ident)

    def get_name(self, xml):
        name = xml.get('name')
        for k,v in iter(self.exceptions_rename):
            found = xml.getroottree().xpath(k, namespaces={'ld': self.ns[1:-1]})
            if found and found[0] is xml:
                # return protobuf name and dfhack name
                return v, name
        if not name:
            name = xml.get(f'{self.ns}anon-name')
        if not name:
            if self.anon_xml != xml:
                self.anon_id += 1
                self.anon_xml = xml
            name = 'anon_' + str(self.anon_id)
        return name, name

    def get_typedef_name(self, xml, name):
        tname = xml.get(f'{self.ns}typedef-name')
        if not tname:
            tname = 'T_' + name
        return tname

    def append_comment(self, xml, line):
        comment = xml.get('comment')
        if comment:
            return line + ' /* ' + comment + ' */'
        return line


    # main renderer

    def render_type_impl(self, xml):
        meta = xml.get(f'{self.ns}meta')
        if meta == 'bitfield-type':
            return self.render_type_bitfield(xml)
        elif meta == 'enum-type':
            return self.render_type_enum(xml)
        elif meta == 'class-type':
            return self.render_struct_type(xml)
        elif meta == 'struct-type':
            return self.render_struct_type(xml)
        raise Exception('not supported: '+xml.tag+': meta='+str(meta))

    def render_field_impl(self, xml, ctx, comment=''):
        for k in self.exceptions_ignore:
            found = xml.getroottree().xpath(k, namespaces={'ld': self.ns[1:-1]})
            if found and found[0] is xml:
                # ignore this field
                return '// ignored field ' + AbstractRenderer.get_name(self, xml)[0]
        meta = xml.get(f'{self.ns}meta')
        if not meta or meta == 'compound':
            return comment + self.render_compound(xml, ctx)
        if meta == 'primitive' or meta == 'number' or meta == 'bytes':
            return self.render_simple_field(xml, ctx)
        elif meta == 'container' or meta == 'static-array':
            return comment + self.render_container(xml, ctx)
        elif meta == 'global':
            return comment + self.render_global(xml, ctx)
        elif meta == 'pointer':
            return comment + self.render_pointer(xml, ctx)
        raise Exception('not supported: '+xml.tag+': meta='+str(meta))
