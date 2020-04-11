import sys
import traceback

from renderer import Renderer


class GlobalTypeRenderer:

    def __init__(self, xml, namespace):
        self.ns = namespace
        self.xml = xml
        assert self.xml.tag == '{%s}global-type' % (self.ns)

    def get_type_name(self):
        tname = self.xml.get('type-name')
        if not tname:
            tname = self.xml.get('name')
        assert tname
        return tname           
        
        

    # main renderer

    def render(self):
        try:
            rdr = Renderer(self.ns)
            typout = rdr.render(self.xml)
            out = 'syntax = "proto3";\n'
            for imp in rdr.imports:
                out += 'import \"%s.proto\";\n' % (imp)
            # TODO: declare package 'df'
            out += '\n' + typout
            return out
        except Exception as e:
            _,value,tb = sys.exc_info()
            print('error rendering type %s at line %d: %s' % (self.get_type_name(), self.xml.sourceline if self.xml.sourceline else 0, e))
            traceback.print_tb(tb)
            return ""

    def render_to_file(self, path):
        fname = self.get_type_name() + '.proto'
        with open(path + '/' + fname, 'w') as fil:
            fil.write(self.render())
        return fname
