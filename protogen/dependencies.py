#!/usr/bin/python3

# requires:
# $ pip install antlr4-python3-runtime

import sys
import argparse
import traceback
import networkx as nx
from antlr4 import *
from parser.DfLexer import DfLexer
from parser.DfParser import DfParser
from antlr4.error.ErrorListener import ErrorListener
from parser.DfParserVisitor import DfParserVisitor


class ThrowingErrorListener(ErrorListener):
   def syntaxError(self, recognizer, offendingSymbol, line, charPositionInLine, msg, e):
      raise Exception("line %d:%d %s" % (line, charPositionInLine, msg))


class DependenciesVisitor(DfParserVisitor):

    PRIMTYPES = ['bool'
                 , 'df-array'
		 , 'df-flagarray'
		 , 'df-linked-list'
		 , 'extra-include'
		 , 'int8_t'
		 , 'int16_t'
		 , 'int32_t'
		 , 'int64_t'
		 , 'long'
		 , 'padding'
		 , 'ptr-string'
		 , 'static-string'
		 , 'stl-bit-vector'
		 , 'stl-string'
		 , 'stl-fstream'
		 , 's-float'
		 , 'uint8_t'
		 , 'uint16_t'
		 , 'uint32_t'
		 , 'uint64_t'
    ]

    def __init__(self):
        self.imports = set()

    def defaultResult(self):
        return []
    
    def aggregateResult(self, aggregate, nextResult: str):
        if nextResult:
            return aggregate + nextResult
        return aggregate
    
    def visitGtype(self, ctx:DfParser.GtypeContext):
        # visit all global types to trace all dependencies
        # (even if they have export='false')
        ch = self.visitChildren(ctx)
        if ch:
            return [ch]

    def visitOther_type(self, ctx:DfParser.Other_typeContext):
        # ignore <global_object> (not a type)
        if not ctx.other(0).GLOBAL_TYPE():
            return self.visitChildren(ctx)

    def visitField(self, ctx):
        for attr in ctx.attribute():
            # ignore fields with attribute: export='false'
            # or attribute: export-as
            if (str(attr.ATTRNAME())=='export' and attr.STRING().getText()[1:-1]=='false') or (str(attr.ATTRNAME())=='export-as'):
                return []
        return self.visitChildren(ctx)

    def visitItem(self, ctx):
        # ignore children of enum items
        return []

    def visitFlag_bit(self, ctx):
        # ignore children of bitfield flags
        return []

    def visitAttribute(self, ctx:DfParser.AttributeContext):
        name = str(ctx.ATTRNAME())
        if name=='type-name' or name=='pointer-type':
            tname = ctx.STRING().getText()[1:-1]
            if tname not in self.PRIMTYPES:
                return [tname]
    
def main():

    # parse args
    parser = argparse.ArgumentParser(description='Build graph of dependencies between types in DFHack structure files.')
    parser.add_argument('inputs', metavar='INFILE', type=str, nargs='+',
                        help='DFHack structure XML file')
    parser.add_argument('--plain', action='store_true', default=False,
                        help='raw output (default=false)')
    parser.add_argument('--separator', '-s', metavar='STR', type=str,
                        default=' ', help='separator between elements of lists (default=" ")')
    args = parser.parse_args()

    all_deps = []
    for f in args.inputs:
        try:
            input_stream = FileStream(f)
            lexer = DfLexer(input_stream)
            stream = CommonTokenStream(lexer)
            parser = DfParser(stream)
            parser.addErrorListener(ThrowingErrorListener())
            tree = parser.datadef()
            visitor = DependenciesVisitor()
            deps = visitor.visitDatadef(tree)
            # add filename as a dependency fo each type
            for d in deps:
                d.extend([f])
            all_deps.extend(deps)
        except Exception as e:
            sys.stderr.write('failed to parse %s' % (f))
            traceback.print_exc(file=sys.stderr)
            exit(1)

    try:
        if not args.plain:
            print('%d file(s), %d global types found' % (len(args.inputs), len(all_deps)))
        
        # output 1 line per type
        for deplist in all_deps:
            print('%s%s%s' % (
                deplist[0],
                ': ' if not args.plain else args.separator,
                args.separator.join(deplist[1:])
            ))
        exit(0)

    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        exit(1)
 
if __name__ == '__main__':
    main()
