#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Attempt to read 
# The main goal is to identify pylibtiff shortcomings, and later on check they are
# corrected.


from __future__ import division, print_function, absolute_import

import numpy
import scipy.ndimage
import sys
import argparse
import logging
from libtiff_ctypes import TIFF
import libtiff.libtiff_ctypes as T  # for the constant names

logging.getLogger().setLevel(logging.DEBUG)

def read_tile(fn, p, x, y, z):
    """Read one given tile in a tiff file -> numpy array"""
    f = TIFF.open(fn, mode='r')

    f.SetDirectory(p)
    logging.info("Looking for tile %d, %d, %d, %d", p, x, y, z)
    num_tcols = f.GetField("TileWidth")
    num_trows = f.GetField("TileLength")
    if num_tcols is None or num_trows is None:
        raise ValueError('The image does not have tiles')

    bits = f.GetField('BitsPerSample')
    sample_format = f.GetField('SampleFormat')
    dtype = f.get_numpy_type(bits, sample_format)

    tile = numpy.zeros((num_trows, num_tcols), dtype=dtype)
    # the numpy array tile should be contiguous on memory
    tile = numpy.ascontiguousarray(tile)
    f.ReadTile(tile, x, y, z, 0)

    return tile


def main(args):
    """
    Handles the command line arguments
    args is the list of arguments passed
    return (int): value to return to the OS as program exit code
    """

    # arguments handling
    parser = argparse.ArgumentParser(description=
                     "Generate a pyramidal version of a TIFF file")

    parser.add_argument("--input", "-i", dest="input", required=True,
                        help="name of the input TIFF file")
    parser.add_argument("--page", "-p", dest="page", type=int, default=0,
                        help="page/directory number")
    parser.add_argument("--tile", "-t", dest="tile", required=True, nargs=3, type=int,
                        help="X,Y,Z position of the tile")

    options = parser.parse_args(args[1:])

    try:
        p = options.page
        x, y, z = options.tile
        im = read_tile(options.input, p, x, y, z)
    except:
        logging.exception("Unexpected error while performing action.")
        return 127

    return 0

if __name__ == '__main__':
    ret = main(sys.argv)
    logging.shutdown()
    exit(ret)