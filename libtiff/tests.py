#!/usr/bin/env python
"""
Ctypes based wrapper to libtiff library.

See TIFF.__doc__ for usage information.

Homepage:  http://pylibtiff.googlecode.com/
"""

from libtiff_ctypes import TIFF

images = [
#    '/home/gstiebler/Projetos/Delmic/images/20140403-105232-songbird brain demo.ome.tiff',
#    '/home/gstiebler/Projetos/Delmic/images/ccd.tiff',
#    '/home/gstiebler/Projetos/Delmic/images/overview.tiff',
#    '/home/gstiebler/Projetos/Delmic/images/sem.tiff',
    '/home/gstiebler/Projetos/Delmic/images/PalaisDuLouvre.tif'
]

for image_name in images:
    tiff = TIFF.open(image_name)
    print tiff.info()
    tiff.read_image()

print 'finish'