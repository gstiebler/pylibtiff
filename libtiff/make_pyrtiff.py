#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Attempt to make a pyramidal TIFF file using pylibtiff
# The main goal is to identify pylibtiff shortcomings, and later on check they are
# corrected.
# One of the main limitation is to be able to chaining of SubIFDs. 

# TODO: check it works with images of size non-multiple of tile size
# => doesn't seem to display properly with display/evince/eog: the right side is messed-up
#    in gimp, the messed-up part is truncated.
#    libpytiff.read_tiles() seems to do the right thing.
# => padding appears to be recommended (with TIFFTAG_IMAGELENGTH/WIDTH not changed.
# So the padding is done at each image resolution independently.
# see TIFF6 norm section 15 (p. 66) => libpytiff.write_tiles()
# seems to already do the right thing.
# This seems to be what is described in http://openslide.org/formats/philips/

# TODO: should compression be supported on tiles? It doesn't seem libpytiff can
# do for now.

# It should create a pyramidal TIFF file as described in , (ie compatible with IIF and ImageMagick).
# It should do the equivalent to ImageMagick:
# convert test.tiff -define tiff:tile-geometry=256x256 ptif:test-pyr-im.tiff
# with VIPS:
# vips tiffsave test.tiff test-pyr-vips.tiff --tile --tile-width=256 --tile-height=256 --pyramid

# To check:
# display test-pyr.tiff # use space/backspace to switch between images
# identify test-pyr.tiff
# tiffinfo test-pyr.tiff
# TODO: also need to try whether IIPImage recognizes it. => cf iipsrv source code? (TPTImage.cc)
# => the only rule is that you put the big image first, and the rest of the sequence
# is the same image with /2 size. It doesn't even check for the NewSubFileType.
# STIFF also support generating pyramid tiff (cf image.c)
# See also http://wiki.freepascal.org/pyramidtiff

# TODO: how to deal with multiple images? It's easy to put just one image + lots
# of reduced images and guess it's pyramidal, but less obvious when there are
# multiple images and many reduced images. => done based just on the order (with
# page number)? Or special tag with link to the other directory. 
# For instance, Adobe Photoshop seems to use SubIFD to link from the main image
# to the reduced images: "All differently
# sized versions are part of the single main IFD, either the main image in that
# IFD, or the image in a SubIFD of that IFD. That should indicate to a reader
# that this is all really the same image. The NewSubfileType tag is used as an
# extra indication of this relation. The SubIFDs tag points only to the first
# SubIFD, and each SubIFD points to the next."
# See BioImageConvert: "OME-TIFF files support only sub-ifd storage in order to keep compatibility"

# For subdir, cf:
# TIFF Trees, in TIFFPM6.pdf
# TIFFSetSubDirectory() -> for browsing
# http://www.asmail.be/msg0055224776.html
# For writing: (= add a SubIFD tag with the given number of directories, and
# libtiff will use it for the next N directories written)
# http://stackoverflow.com/questions/11959617/in-a-tiff-create-a-sub-ifd-with-thumbnail-libtiff


# In http://www.digitalpreservation.gov/formats/fdd/fdd000237.shtml:
# Photoshop uses NewSubFileType = REDUCEDIMAGE.
# They say ImageMagick uses = PAGE, but in my experiments, it uses REDUCEDIMAGE too

# See also Aperio format: http://www.aperio.com/documents/api/Aperio_Digital_Slides_and_Third-party_data_interchange.pdf page 14:
# The first image in an SVS file is always the baseline image (full resolution). This image is always tiled, usually with a tile size of 240x240 pixels. The second image is always a thumbnail, typically with dimensions of about 1024x768 pixels. Unlike the other slide images, the thumbnail image is always stripped. Following the thumbnail there may be one or more intermediate “pyramid” images. These are always compressed with the same type of compression as the baseline image, and have a tiled organization with the same tile size.
# 
# Optionally at the end of an SVS file there may be a slide label image, which is a low resolution picture taken of the slide’s label, and/or a macro camera image, which is a low resolution picture taken of the entire slide. The label and macro images are always stripped.



from __future__ import division, print_function, absolute_import

import numpy
import scipy.ndimage
import sys
import math
import argparse
import logging
from libtiff_ctypes import TIFF
import libtiff.libtiff_ctypes as T  # for the constant names
import os


logging.getLogger().setLevel(logging.DEBUG)

TILE_SIZE = 256 # Size of the tiles in pixels (they are always square)


def rescale_hq(data, shape):
    """
    Resize the image to the new given shape (smaller or bigger). It tries to
    smooth the pixels. Metadata is updated.
    data (DataArray of shape YX): data to be rescaled
    shape (2 int>0): the new shape of the image (Y,X). The new data will fit
      precisely, even if the ratio is different.
    return (DataArray of shape YX): The image rescaled. If the metadata contains
      information that is linked to the size (e.g, pixel size), it is also
      updated.
    """
    # Note: as the scale is normally a power of 2, the whole function could be
    # very optimised (by just a numpy.mean).
    out = numpy.empty(shape, dtype=data.dtype)
    scale = (shape[0] / data.shape[0], shape[1] / data.shape[1])
    if len(shape) == 3:
        scale = scale + (1,)
    scipy.ndimage.interpolation.zoom(data, zoom=scale, output=out, order=1, prefilter=False)
    return out


def read_image(fn):
    """Read tiff as input -> numpy array"""
    f = TIFF.open(fn, mode='r')
    # TODO: move this code to libpytiff.read_image()?
    if f.IsTiled():
        bits = f.GetField('BitsPerSample')
        sample_format = f.GetField('SampleFormat')
        typ = f.get_numpy_type(bits, sample_format)
        im = f.read_tiles(typ)
    else:
        im = f.read_image() # Fist image
    if im.ndim > 2:
        logging.warning("Only greyscale images supported")
    return im

    # open each image/page as a separate image
#     data = []
#     for image in f.iter_images():
#         data.append(image)


def write_image(fn, im):
    """
    Write an TIFF image, in standard mode
    """
    f = TIFF.open(fn, mode='w')
    f.write_image(im)
    f.close()

def set_image_tags(tiff_file, im, compression=None):
    """
    Set the required TIFF tags for the given image
    """
    # TODO: These tags are set by write_image(), but not by write_tiles()
    # => also put it in write_tiles()? Or should that function be able to be
    # called multiple times, which is the reason this is not done?
    
    shape = im.shape
    bits = im.itemsize * 8
    if im.dtype in numpy.sctypes['float']:
        sample_format = T.SAMPLEFORMAT_IEEEFP
    elif im.dtype in numpy.sctypes['uint']+[numpy.bool]:
        sample_format = T.SAMPLEFORMAT_UINT
    elif im.dtype in numpy.sctypes['int']:
        sample_format = T.SAMPLEFORMAT_INT
    elif im.dtype in numpy.sctypes['complex']:
        sample_format = T.SAMPLEFORMAT_COMPLEXIEEEFP
    else:
        raise NotImplementedError("%s" % im.dtype)
    
    tiff_file.SetField(T.TIFFTAG_BITSPERSAMPLE, bits)
    tiff_file.SetField(T.TIFFTAG_SAMPLEFORMAT, sample_format)
    tiff_file.SetField(T.TIFFTAG_ORIENTATION, T.ORIENTATION_TOPLEFT)
    tiff_file.SetField(T.TIFFTAG_PHOTOMETRIC, T.PHOTOMETRIC_MINISBLACK)
    # TODO: currently libpytiff only supports 3D tiled images in "separate" planes
    # Is it even possible with TIFF to use Tiles + CONTIG? 
    tiff_file.SetField(T.TIFFTAG_PLANARCONFIG, T.PLANARCONFIG_CONTIG)

    tiff_file.SetField(T.TIFFTAG_IMAGELENGTH, shape[0])
    tiff_file.SetField(T.TIFFTAG_IMAGEWIDTH, shape[1]) # TODO: why required by write_tiles()?
    # TODO: should be the first dim, if ndim == 3
    # TODO: not needed if == 1, as it's the default
    tiff_file.SetField(T.TIFFTAG_IMAGEDEPTH, 1) # If C as first dim => required

    if compression:
        logging.info("using compression %s", compression)
    compression = tiff_file._fix_compression(compression)
    tiff_file.SetField(T.TIFFTAG_COMPRESSION, compression)
    if (compression == T.COMPRESSION_LZW and
        sample_format in [T.SAMPLEFORMAT_INT, T.SAMPLEFORMAT_UINT]):
        # This field can only be set after compression and before
        # writing data. Horizontal predictor often improves compression,
        # but some rare readers might support LZW only without predictor.
        tiff_file.SetField(T.TIFFTAG_PREDICTOR, T.PREDICTOR_HORIZONTAL)

def generate_pyramid(ofn, images, compressed=False):

    compression = T.COMPRESSION_LZW if compressed else None

    # Create new Tiff file
    f = TIFF.open(ofn, mode='w')
    logging.info("Generating image %s", ofn)

    for im in images:
        shape = im.shape
        # Store the complete image, with tiles
        f.SetField(T.TIFFTAG_PAGENAME, "Full image") # Just example of metadata

        logging.info("Writing initial image at size %s", shape)
        #set_image_tags(f, im, compression)
        n = int(math.ceil(math.log(max(shape) / TILE_SIZE, 2)))
        logging.debug("Will generate %d sub-images", n)
        # LibTIFF will automatically write the next N directories as subdirectories
        # when this tag is present.
        f.SetField(T.TIFFTAG_SUBIFD, [0] * n, count=n)
        # assums that if the array has 3 dimensions, the 3rd dimension is color
        is_rgb = len(im.shape) == 3
        f.write_tiles(im, TILE_SIZE, TILE_SIZE, compression, is_rgb)

        # Until the size is < 1 tile:
        z = 0
        while shape[0] > TILE_SIZE and shape[1] > TILE_SIZE:
            # Resample the image by 0.5x0.5
            # Add it as subpage, with tiles
            z += 1
            shape = (im.shape[0] // 2**z, im.shape[1] // 2**z)
            if len(im.shape) == 3:
                shape = shape + (3,)
            logging.info("Computing image at size %s", shape)
            subim = rescale_hq(im, shape)

            # Before writting the actual data, we set the special metadata
            f.SetField(T.TIFFTAG_SUBFILETYPE, T.FILETYPE_REDUCEDIMAGE) # TODO: & T.FILETYPE_PAGE ? ImageMagick only put REDUCEDIMAGE

            # set_image_tags(f, subim, compression)
            f.write_tiles(subim, TILE_SIZE, TILE_SIZE, compression, is_rgb)


def read_pyramid(file_name, base_path, image_name):

    def write_image(im, base_path, count, n):
        out_file = "%s/%s/image%d_sub%d.tiff" % (base_path, image_name, count, n)
        a = TIFF.open(out_file, "w")
        a.write_image(im, None, len(im.shape) == 3)

    f = TIFF.open(file_name, mode='r')

    count = 0
    for im in f.iter_images():
        # get an array of offsets, one for each subimage
        sub_ifds = f.GetField(T.TIFFTAG_SUBIFD)

        directory = "%s/%s" % (base_path, image_name)
        if not os.path.exists(directory):
            os.makedirs(directory)

        write_image(im, base_path, count, 0)

        for n in xrange(len(sub_ifds)):
            # set the offset of the current subimage
            f.SetSubDirectory(sub_ifds[n])
            # read the subimage
            im = f.read_image()

            write_image(im, base_path, count, n + 1)

        f.SetDirectory(count)
        count += 1


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
    parser.add_argument("--compressed", "-z", dest="compressed", action="store_true", default=False,
                        help="activates lossless compression of the data")
    parser.add_argument("--output", "-o", dest="output", required=True,
                        help="name of the output TIFF file")

    options = parser.parse_args(args[1:])

    try:
        im = read_image(options.input)
        logging.info("Image size is %s", im.shape)
#        write_image(options.output, im)
        generate_pyramid(options.output, im, compressed=options.compressed)
    except:
        logging.exception("Unexpected error while performing action.")
        return 127

    return 0

def test_pyramids():
    base_path = '/home/gstiebler/Projetos/Delmic/images'
    image_names = ['overview', 'sem', 'ccd']
    
    # write each image in a different pyramid image
    for image_name in image_names:
        full_file_name = "%s/%s.tiff" % (base_path, image_name)
        output_file_name = "%s/%s-pyr.tiff" % (base_path, image_name)
        try:
            tiff = TIFF.open(full_file_name, mode='r')
            im = tiff.read_image()
            #tags_to_copy = ["BitsPerSample", "SampleFormat", "SamplesPerPixel",
            #                "PlanarConfig", "Photometric"]
            generate_pyramid(output_file_name, [im], compressed=False)
            read_pyramid(output_file_name, base_path, image_name)
        except:
            logging.exception("Unexpected error while performing action.")
            return 127

    # write all images in the same pyramid image 
    images = []
    for image_name in image_names:
        full_file_name = "%s/%s.tiff" % (base_path, image_name)
        try:
            tiff = TIFF.open(full_file_name, mode='r')
            im = tiff.read_image()
            images.append(im)
        except:
            logging.exception("Unexpected error while performing action.")
            return 127

    all_images_name = "all-images"
    output_file_name = "%s/%s-pyr.tiff" % (base_path, all_images_name)
    generate_pyramid(output_file_name, images, compressed=False)
    read_pyramid(output_file_name, base_path, all_images_name)

    return 0

if __name__ == '__main__':
    # ret = main(sys.argv)
    ret = test_pyramids()
    logging.shutdown()
    exit(ret)
