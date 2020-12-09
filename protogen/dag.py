#!/usr/bin/python3

# requires:
# $ pip install networkx

import sys
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
    group = parser.add_argument_group('commands').add_mutually_exclusive_group()
    group.add_argument('--ancestors', metavar='TYPE', type=str, nargs='+', default=[],
                        help='list all ancestors of given nodes')
    group.add_argument('--sources', metavar='TYPE', type=str, nargs='*', default=None,
                        help='list all sources of given nodes (default: all nodes)')
    args = parser.parse_args()

    # read graph
    G = nx.DiGraph()
    for f in args.inputs:
        try:
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
            fp.close()

    if not args.plain:
        print('%d file(s), read %d nodes and %d edges' % (len(args.inputs), G.number_of_nodes(), G.number_of_edges()))

    try:
        # list all ancestors of the given nodes
        if args.ancestors:
            deps = set()
            for t in args.ancestors:
                deps.update([t])
                deps.update(nx.ancestors(G, t))
            print('%s' % (args.separator.join(list(deps))))
            exit(0)

        # list all sources of the given nodes
        if args.sources is not None:
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
            if sources:
                print(args.separator.join(list(sources)))
            exit(0)
    
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        exit(1)
 
if __name__ == '__main__':
    main()
