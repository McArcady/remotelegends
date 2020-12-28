#!/usr/bin/python3

# requires:
# $ pip install networkx

import sys
import re
import argparse
import traceback
import networkx as nx

def main():

    # parse args
    parser = argparse.ArgumentParser(description='Explore a directed acyclic graph.')
    parser.add_argument('inputs', metavar='INFILE', type=str, nargs='+',
                        help='DAG file')
    parser.add_argument('--plain', action='store_true', default=False,
                        help='raw output (default=false)')
    parser.add_argument('--separator', '-s', metavar='STR', type=str,
                        default=' ', help='separator between elements of lists (default=" ")')
    parser.add_argument('-1', dest='one', action='store_true', default=False,
                        help='output 1 element per line')
    parser.add_argument('--exclude', metavar='REGEX', type=str,
                        help='exclude nodes matching REGEX from the result')
    group = parser.add_argument_group('commands').add_mutually_exclusive_group()
    group.add_argument('--ancestors', metavar='TYPE', type=str, nargs='+', default=[],
                        help='list all ancestors of given nodes, including themselves')
    group.add_argument('--successors', metavar='TYPE', type=str, nargs='+', default=[],
                        help='list direct successors of given nodes')
    group.add_argument('--sources', metavar='TYPE', type=str, nargs='*', default=None,
                        help='list all sources of given nodes (default: all nodes)')
    group.add_argument('--path', metavar='SOURCE TARGET', type=str, nargs='2', default=[],
                        help='list all paths from SOURCE to TARGET')
    args = parser.parse_args()

    # read graph
    G = nx.DiGraph()
    for f in args.inputs:
        try:
            fp = None
            with open(f) as fp:
                line = fp.readline()
                while line:
                    tokens = line.split()
                    if not tokens:
                        continue
                    node = tokens[0]
                    for dep in tokens[1:]:
                        G.add_edge(dep, node)
                    line = fp.readline()
        except Exception as e:
            sys.stderr.write('error parsing %s' % (f))
            traceback.print_exc(file=sys.stderr)
            exit(1)
        finally:
            if fp:
                fp.close()

    if not args.plain:
        print('read %d file(s), %d nodes and %d edges' % (len(args.inputs), G.number_of_nodes(), G.number_of_edges()))

    try:
        # list all ancestors of the given nodes
        if args.ancestors:
            deps = set()
            for t in args.ancestors:
                deps.update([t])
                deps.update(nx.ancestors(G, t))
            result = list(deps)

        # list all direct successors of the given nodes
        elif args.successors:
            deps = set()
            for t in args.successors:
                deps.update(G.successors(t))
            result = list(deps)

        # list all sources of the given nodes
        elif args.sources is not None:
            sources = set()
            nodes = set()
            for n in args.sources:
                nodes.update(nx.ancestors(G, n))
            if nodes:
                view = G.in_degree(list(nodes))
            else:
                view = G.in_degree()
            for node, degree in list(view):
                if degree == 0:
                    sources.update([node])
            result = list(sources)

        # list all paths from 'source' to 'target'
        elif args.path:
            if len(args.path) != 2:
                parser.print_help()
                exit(1)
            result = ''
            for path in nx.all_simple_paths(G, source=args.path[0], target=args.path[1]):
                print(','.join([n for n in path]) + '\n')
            exit(0)

        if args.exclude:
            result = [r for r in result if not re.match(args.exclude, r)]
        if args.one:
            args.separator = '\n'
        if result:
            print(args.separator.join(result), end='')
        exit(0)
    
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        exit(1)
 
if __name__ == '__main__':
    main()
