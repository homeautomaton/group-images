import sys
import os
import re
import time
import json
import copy
import argparse
from textwrap import dedent

# Theory of operation:
#     read input of image characteristics in the form
#     [ {"file":"x.jpg","grays":[8692,13411,16458...]}, ... ]
#     This can be produced with something like:
#         ( echo "["
#         for f in JPGS_00*/*.jpg; do x=$(convert -resize 10x10'!' $f -colorspace Gray  txt: | grep -v Image | sed -e 's/,//' -e 's/,.*//' -e 's/.*(//'); echo $f $x; done | \
#         sed -e 's/^/{"file":"/' -e 's/ /","grays":[/' -e 's/$/]},/' -e 's/ /,/g' ; echo "]" ) >jpg_levels &
#     Each of the gray values will be used to sort the whole list, finding possible adjancies where images share a value close by.
#     A running list of pool-size will be considered as neighbors if their gray-scale difference is at or below threshold.
#     Once all sorting/pooling passes are completed, the top neighbors are considered for adjacency, applying the adj_threshold to the average of all gray-scale difference.
#     Equivalence classes are determined by traversing the adjacencies.
#     The smallest equivalence classes should contain the most interesting features.

group_size = {}

def neighbor( data, m, n, p, threshold ):
    if m == n: print( 'wtf' )
    if abs( data[ m ][ 'grays' ][ p ] - data[ n ][ 'grays' ][ p ] ) > threshold: return
    if 'pool' not in data[ m ]:
        data[ m ][ 'pool' ] = {}
    if n not in data[ m ][ 'pool' ]:
        data[ m ][ 'pool' ][ n ] = 0
    data[ m ][ 'pool' ][ n ] += 1

def average_diff( data, sample_cnt, m, n ):
    diff = 0
    for p in range( sample_cnt ):
        diff += abs( data[ m ][ 'grays' ][ p ] - data[ n ][ 'grays' ][ p ] )
    return diff / sample_cnt

def walk( data, index, group ):
    data[ index ][ 'group' ] = group
    if group not in group_size: group_size[ group ] = 0
    group_size[ group ] += 1
    for adj in data[ index ][ 'adjacent' ]:
        if 'group' not in data[ adj ]:
            walk( data, adj, group )

def main():
    p = argparse.ArgumentParser( description='Group images by similarity' )
    p.add_argument( '-p', '--pool-size', metavar='10', type=int, default=10, help='Number of nearby images from every sorting pass to consider as final adjacencies' )
    p.add_argument( '-a', '--adjacencies', metavar='4', type=int, default=4, help='Maximum number of final adjacencies to track per images' )
    p.add_argument( '-t', '--threshold', metavar='20', type=int, default=20, help='Threshold for specific difference to consider for pool' )
    p.add_argument( '-T', '--adj_threshold', metavar='4000', type=int, default=4000, help='Threshold for average difference to consider non-adjacent (lower number makes more equivalence classes' )
    p.add_argument( '-l', '--limit', metavar='5000', type=int, default=0, help='Only process a limited number of records from input file (for testing)' )
    p.add_argument( '-f', '--file', metavar='FILE', help='File containing JSON image characteristics' )

    try:
        args = p.parse_args( )
    except BaseException as e:
        if e.code != 0:
            print( '' )
        sys.exit()

    if not args.file:
        print( '-f|--file is required' )
        sys.exit()

    with open( args.file, 'r' ) as openfile:
        data = json.load( openfile )

    if args.limit > 0 and len( data ) > args.limit:
        data = data[ : args.limit ]

    sample_cnt = len( data[ 0 ][ 'grays' ] )

    for n in range( len( data ) ):
        data[n][ 'index' ] = n

    indexed_data = copy.deepcopy( data )

    for sort_pass in range( sample_cnt ):
        data.sort( key=lambda img: img[ 'grays' ] [ sort_pass ] )
        for n in range(len(data)):
            for i in range( min( n - 1, args.pool_size ) ):
                neighbor( indexed_data, data[ n - i - 1 ][ 'index' ], data[ n ][ 'index' ], sort_pass, args.threshold )

    for img in indexed_data:
        averages = []
        img[ 'adjacent' ] = []
        for n in img[ 'pool' ]:
            avg = average_diff( indexed_data, sample_cnt, img[ 'index' ], n )
            if avg <= args.adj_threshold:
                averages.append( { "adjacent" : n, "avg" : avg } )
        averages.sort( key=lambda a: a[ 'avg' ] )
        for n in range( min( args.adjacencies, len( averages ) ) ):
           img[ 'adjacent' ].append( averages[ n ][ 'adjacent' ] )

    group = 1
    for img in indexed_data:
        if 'group' not in img:
            walk( indexed_data, img[ 'index' ], group )
            group += 1
    print( group )
    print( repr( group_size ) )

    ### print( repr( indexed_data ) )
if __name__ == '__main__':
    main()

#    try:
#    #except EOFError as error:
#    #    pass
#    #except KeyboardInterrupt as error:
#    #    pass
