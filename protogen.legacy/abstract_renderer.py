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
        self.exceptions_enum = []
        # ignore fields with no attribute 'export' ?
        self.ignore_no_export = True
        # generate comment for ignored fields ?
        self.comment_ignored = False

    def set_ignore_no_export(self, b):
        self.ignore_no_export = b
        return self

    def set_comment_ignored(self, b):
        self.comment_ignored = b
        return self

    def copy(self, target):
        target.exceptions_ignore = self.exceptions_ignore
        target.exceptions_rename = self.exceptions_rename
        target.exceptions_index = self.exceptions_index
        target.exceptions_enum = self.exceptions_enum
        target.ignore_no_export = self.ignore_no_export
        target.comment_ignored = self.comment_ignored

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

    def add_exception_enum(self, tname):
        self.exceptions_enum.append(tname)
        return self

    def ident(self, xml, extra_ident=0):
        ident = xml.get(f'{self.ns}level') or 1
        return '  ' * (int(ident) + extra_ident)

    def get_name(self, xml):
        dfname = xml.get('name')
        pbname = None
        for k,v in iter(self.exceptions_rename):
            found = xml.getroottree().xpath(k, namespaces={'ld': self.ns[1:-1]})
            if found and found[0] is xml:
                # rename protobuf name
                pbname = v
        if not dfname:
            dfname = xml.get(f'{self.ns}anon-name')
        if not dfname:
            if self.anon_xml != xml:
                self.anon_id += 1
                self.anon_xml = xml
            dfname = 'anon_' + str(self.anon_id)
        if not pbname:
            pbname = dfname
        # protobuf field names are lowercase, except enum items
        if xml.tag != 'enum-item':
            pbname = pbname.lower()
        return pbname, dfname

    def get_typedef_name(self, xml, name):
        tname = xml.get(f'{self.ns}typedef-name')
        if not tname:
            tname = self.get_type_name(xml, name)
        return tname

    def get_type_name(self, xml, name=None):
        tname = xml.get('type-name')
        if not tname:
            if not name:
                name = AbstractRenderer.get_name(self, xml)[0]
            tname = 'T_' + name
        return tname

    def append_comment(self, xml, line=''):
        if line:
            line += ' '
        comment = xml.get('comment')
        if comment:
            return line + '/* ' + comment + ' */\n'
        return line + '\n'

    
    # struct / class
        
    def render_type_struct(self, xml, tname=None, ctx=None):
        if not ctx:
            ctx = self.create_context()
        if not tname:
            tname = xml.get('type-name')
        out = self._render_struct_header(xml, tname, ctx)
        value = 1
        parent = xml.get('inherits-from')
        if parent:
            out += self._render_struct_parent(xml, parent, ctx)
            value += 1        
        for item in xml.findall(f'{self.ns}field'):
            field, value = self._render_struct_field(item, value, ctx)
            out += field
        methods = xml.find('virtual-methods')
        if methods!=None and len(methods):
            for method in methods.findall('vmethod'):
                field, value = self._render_class_method(method, value, ctx)
                out += field
        out += self._render_struct_footer(xml, ctx)
        return out

    def _render_class_method(self, xml, value, ctx):
        name = AbstractRenderer.get_name(self, xml)[0]
        assert(name)
        tname = xml.get('ret-type')
        if not tname or not name.startswith('get'):
            # method is not a regular getter
            return '', value
        ctx = self.create_context()
        ctx.value = value
        field = self.render_field(xml, ctx)
        value += 1
        return field, value
    

    # main renderer

    def render_type_impl(self, xml):
        meta = xml.get(f'{self.ns}meta')
        if meta == 'bitfield-type':
            return self.render_type_bitfield(xml)
        elif meta == 'enum-type':
            return self.render_type_enum(xml)
        elif meta == 'class-type':
            return self.render_type_struct(xml)
        elif meta == 'struct-type':
            return self.render_type_struct(xml)
        raise Exception('not supported: '+xml.tag+': meta='+str(meta))

    def render_field_impl(self, xml, ctx):
        ignore = False        
        name = xml.get('name')
        export = xml.get('export')
        export_as = xml.get('export-as')
        if export_as:
            # convert type
            return self.render_field_conversion(xml, ctx)
        elif export==None and self.ignore_no_export:
            ignore = True
        elif (name and name.startswith('unk_')) or (export and export == 'false'):
            ignore = True

        # if (name and name.startswith('unk_')) or export!='true':
        else:
            for k in self.exceptions_ignore:
                found = xml.getroottree().xpath(k, namespaces={
                    'ld': self.ns[1:-1],
                    're': 'http://exslt.org/regular-expressions'
                })
                if found and xml in found:
                    ignore = True
                    break
        if ignore:
            # ignore this field
            if self.comment_ignored:
                return self.ident(xml) + '/* ignored field %s */\n' % (name or 'anon')
            else:
                return ''
        else:
            # export all sub-elements
            for sub in xml.iter():
                sub.set('export', 'true')
        meta = xml.get(f'{self.ns}meta')
        if not meta and xml.tag == 'vmethod':
            return self.render_field_method(xml, ctx)
        if not meta or meta == 'compound':
            return self.render_field_compound(xml, ctx)
        if meta == 'primitive' or meta == 'number' or meta == 'bytes':
            return self.render_field_simple(xml, ctx)
        elif meta == 'global':
            return self.render_field_global(xml, ctx)
        elif meta == 'container' or meta == 'static-array':
            return self.render_field_container(xml, ctx)
        elif meta == 'pointer':
            return self.render_field_pointer(xml, ctx)
        raise Exception('not supported: '+xml.tag+': meta='+str(meta))
