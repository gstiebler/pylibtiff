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

    count = 0
    for im in f.iter_images():

        if count == p:
            # get an array of offsets, one for each subimage
            sub_ifds = f.GetField(T.TIFFTAG_SUBIFD)
            if z > 0:
                f.SetSubDirectory(sub_ifds[z - 1])
            tile = f.read_one_tile(x, y)
            break

        f.SetDirectory(count)
        count += 1

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
    parser.add_argument("--output", "-o", dest="output", required=True,
                        help="name of the output TIFF file")

    options = parser.parse_args(args[1:])

    try:
        p = options.page
        x, y, z = options.tile
        im = read_tile(options.input, p, x, y, z)
        out = TIFF.open(options.output, mode='w')
        out.write_image(im, None, len(im.shape) == 3)
        print("tile saved")
    except:
        logging.exception("Unexpected error while performing action.")
        return 127

    return 0

if __name__ == '__main__':
    ret = main(sys.argv)
    logging.shutdown()
    exit(ret)