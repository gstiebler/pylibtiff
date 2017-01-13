#!/usr/bin/env python
"""
Ctypes based wrapper to libtiff library.

See TIFF.__doc__ for usage information.

Homepage:  http://pylibtiff.googlecode.com/
"""

from libtiff_ctypes import TIFF
from libtiff.tiff_h_4_0_6 import *

images = [
#    '/home/gstiebler/Projetos/Delmic/images/20140403-105232-songbird brain demo.ome.tiff',
#    '/home/gstiebler/Projetos/Delmic/images/ccd.tiff',
#    '/home/gstiebler/Projetos/Delmic/images/overview.tiff',
#    '/home/gstiebler/Projetos/Delmic/images/sem.tiff',
#    '/home/gstiebler/Projetos/Delmic/images/PalaisDuLouvre.tif'
]

'''
for image_name in images:
    tiff = TIFF.open(image_name)
    print tiff.info()
    tiff.read_image()
'''

fpath = '/home/gstiebler/Projetos/Delmic/images/'
ext = '.tiff'
file_name_in = "%sccd%s" % (fpath, ext)
tiff = TIFF.open(file_name_in, "r")
arr = tiff.read_image()

file_name_im_save = "%sccd-saved%s" % (fpath, ext)
tiff_im_save = TIFF.open(file_name_im_save, "w")
tiff_im_save.write_image(arr)

file_name_tiles_save = "%sccd-tiles%s" % (fpath, ext)
tiff_tiles_save = TIFF.open(file_name_tiles_save, "w")
tiff_tiles_save.SetField(TIFFTAG_TILEWIDTH, 256)
tiff_tiles_save.SetField(TIFFTAG_TILELENGTH, 256)
tiff_tiles_save.SetField(TIFFTAG_IMAGEWIDTH, arr.shape[1])
tiff_tiles_save.SetField(TIFFTAG_IMAGELENGTH, arr.shape[0])
tiff_tiles_save.SetField(TIFFTAG_BITSPERSAMPLE, 16)
tiff_tiles_save.SetField(TIFFTAG_SAMPLEFORMAT, SAMPLEFORMAT_UINT)
tiff_tiles_save.SetField(TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_MINISBLACK)
# tiff_tiles_save.SetField(TIFFTAG_IMAGEDEPTH, 1)
# tiff_tiles_save.SetField(TIFFTAG_SAMPLESPERPIXEL, 1)
# tiff_tiles_save.SetField(TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG)
# tiff_tiles_save.SetField(TIFFTAG_ROWSPERSTRIP, 2)
# tiff_tiles_save.SetField(TIFFTAG_ORIENTATION, ORIENTATION_TOPLEFT)
# tiff_tiles_save.SetField(TIFFTAG_COMPRESSION, COMPRESSION_JPEG)
tiff_tiles_save.write_tiles(arr)

print 'finish'