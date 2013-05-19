#!/usr/bin/env python -O 
# -*- coding: utf-8 -*-

"""
 * =========================================================================
 * This file is part of NITRO
 * =========================================================================
 * 
 * (C) Copyright 2004 - 2010, General Dynamics - Advanced Information Systems
 *
 * NITRO is free software; you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation; either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public 
 * License along with this program; if not, If not, 
 * see <http://www.gnu.org/licenses/>.
 *
 *
"""

"""
This is an example of how to generate your own NITF files
from scratch

You could also read in a JPG file, creating a NITF with the
decompressed raw bytes, using the PIL library.

Notice how easy it is to change fields in the NITF
"""
import os, sys, array, unittest, random, Image
from nitf import *
from tempfile import mkstemp
from datetime import datetime
import logging

image = Image.open("wright.jpeg")


logging.basicConfig(level=logging.DEBUG, stream=sys.stdout,
                    format='%(asctime)s %(levelname)s %(message)s')


NITF_21_DATE_FORMAT = '%Y%m%d%H%M%S'


class TestCreator(unittest.TestCase):
    
    def setUp(self):
        """ just sets up mappings of default field values """
        fieldmap = {}
        fieldmap['header'] = {
            'fileHeader' : 'NITF', 
            'fileVersion' : '02.10', 
            'systemType' : 'BF01', 
            'classification' : 'U', 
            'originatorName' : 'Carlos', 
            'complianceLevel' : 99,
            'encrypted' : 0,
            'originStationID' : 'STAR',
            'fileDateTime' : datetime.now().strftime(NITF_21_DATE_FORMAT),
        }
        fieldmap['image'] = {
            'filePartType' : 'IM',
            'classificationSystem' : 'U',
            'imageDateAndTime' : datetime.now().strftime(NITF_21_DATE_FORMAT),
        }
        
        fieldmap['graphic'] = {
            'filePartType' : 'SY',
            'securityClass' : 'U',
            'encrypted' : 0,
            'color' : 'C',
            'stype' : 'C',
        }
        self.fieldmap = fieldmap
        
        self.inputs = sys.argv[1:]
        self.hasInput = len(self.inputs) > 0
        
    
    
    def test_make_image_nitf(self):
        self.make_image_nitf()
    
    def star_make_image_nitf(self, image):
        record = Record()
        pass
    
    def make_image_nitf(self, numBands=1, width=256, height=256):
        """ makes a nitf, with artificial image data """
        record = Record()
        if self.fieldmap.has_key('header'):
            for field, value in self.fieldmap['header'].iteritems():
                if field in record.header:
                    record.header[field] = str(value)
        
        #create a random pattern size
        csize = random.randint(0, 255)
        alldata = []
        for i in range(height):
            for j in range(width):
                for k in range(numBands):
                    swap = (j % csize) % 2 != 0
                    alldata.append((j % csize) % 2 == 0 and (not swap and 255 or 0))
        alldata = str(alldata)
        
        #add an image segment
        segment = record.newImageSegment()
        if self.fieldmap.has_key('image'):
            for field, value in self.fieldmap['image'].iteritems():
                if field in segment.subheader:
                    segment.subheader[field] = str(value)
        
        #for now, I just put in these as defaults
        #obviously, too large of an image will cause problems with the block-size...
        segment.addBands(numBands)
        segment.subheader['numrows'] = height
        segment.subheader['numcols'] = width
        segment.subheader['numBitsPerPixel'] = 8
        segment.subheader['actualBitsPerPixel'] = 8
        segment.subheader['pixelValueType'] = 'INT'
        segment.subheader['pixelJustification'] = 'R'
        segment.subheader['imageCompression'] = 'NC'
        segment.subheader['imageDisplayLevel'] = 1
        segment.subheader['imageAttachmentLevel'] = 0
        segment.subheader['imageRepresentation'] = numBands == 1 and 'MONO' or 'MULTI'
        segment.subheader['imageCategory'] = 'VIS'
        segment.subheader['imageSyncCode'] = '0'
        segment.subheader['imageLocation'] = '0000000000'
        segment.subheader['imageMode'] = 'B'
        segment.subheader['numBlocksPerCol'] = 1
        segment.subheader['numBlocksPerRow'] = 1
        segment.subheader['numPixelsPerHorizBlock'] = width
        segment.subheader['numPixelsPerVertBlock'] = height
        
        #setup image source
        imagesource = ImageSource()
        for i in range(numBands):
            imagesource.addBand(MemoryBandSource(alldata, len(alldata)/numBands, i, 1, numBands-1))
        
        try:
            handle, outfile = mkstemp(suffix='.ntf')
            os.close(handle)
            writer = Writer()
            outhandle = IOHandle(outfile, IOHandle.ACCESS_WRITEONLY, IOHandle.CREATE)
            if writer.prepare(record, outhandle):
                imagewriter = writer.newImageWriter(0)
                if imagewriter:
                    imagewriter.attachSource(imagesource)
                    writer.write()
                    logging.info('Successfully Wrote NEW NITF: %s\n' % outfile)
            outhandle.close()
        except Exception, e:
            print e
        else:
            handle = IOHandle(outfile)
            rec = Reader().read(handle)
            logging.info(str(rec.header))
            handle.close()
            os.unlink(outfile)

def dump_image(subheader, index, imageReader, outDir=None, baseName=None):
    window = SubWindow()
    window.numRows = subheader['numRows'].intValue()
    window.numCols = subheader['numCols'].intValue()
    window.bandList = range(subheader.getBandCount())
    nbpp = subheader['numBitsPerPixel'].intValue()
    bandData = imageReader.read(window)
    
    if not outDir: outDir = os.getcwd()
    if not baseName: baseName = os.path.basename(os.tempnam())
    
    outNames = []
    for band, data in enumerate(bandData):
        outName = '%s_%d__%d_x_%d_%d_band_%d.jpg' % (
             baseName, index, window.numRows, window.numCols, nbpp, band)
        outName = os.path.join(outDir, outName)
        
        #TODO actually check the image type and set the mode properly
        im = Image.frombuffer('L', (window.numCols, window.numRows), data, 'raw', 'L', 0, 1)
        im.save(outName)
        outNames.append(outName)
        logging.info('Wrote band data to file %s' % outName)
    return outNames



def dump_images(fileName, outDir=None):
    if not outDir: outDir = os.getcwd()
    if not os.path.exists(outDir): os.makedirs(outDir)
    
    handle = IOHandle(fileName)
    reader = Reader()
    record = reader.read(handle)
    logging.info('Dumping file: %s' % fileName)
    
    for i, segment in enumerate(record.getImages()):
        logging.info('--- Image [%d] ---' % i)
        imReader = reader.newImageReader(i)
        dump_image(segment.subheader, i, imReader, outDir, os.path.basename(fileName))
    handle.close()
    
def insert_image(filename, index, outDir=None):
    reader = Reader()
    imReader = reader.newImageReader(filename)
    
    window = SubWindow()
    window.numRows = subheader['numRows'].intValue()
    window.numCols = subheader['numCols'].intValue()
    window.bandList = range(subheader.getBandCount())
    nbpp = subheader['numBitsPerPixel'].intValue()
    bandData = imageReader.read(window)
    
    if not outDir: outDir = os.getcwd()
    if not baseName: baseName = os.path.basename(os.tempnam())
    
    outNames = []
    for band, data in enumerate(bandData):
        outName = '%s_%d__%d_x_%d_%d_band_%d.jpg' % (
             baseName, index, window.numRows, window.numCols, nbpp, band)
        outName = os.path.join(outDir, outName)
        
        #TODO actually check the image type and set the mode properly
        im = Image.frombuffer('L', (window.numCols, window.numRows), data, 'raw', 'L', 0, 1)
        im.save(outName)
        outNames.append(outName)
        logging.info('Wrote band data to file %s' % outName)
    return outNames

def get_images(fileName, outDir=None):
    if not outDir: outDir = os.getcwd()
    if not os.path.exists(outDir): os.makedirs(outDir)
    
    handle = IOHandle(fileName)
    reader = Reader()
    record = reader.read(handle)
    logging.info('Dumping file: %s' % fileName)
    
    for i, segment in enumerate(record.getImages()):
        logging.info('--- Image [%d] ---' % i)
        imReader = reader.newImageReader(i)
        dump_image(segment.subheader, i, imReader, outDir, os.path.basename(fileName))
    handle.close()

#if __name__ == '__main__':
#    unittest.main(argv=sys.argv[0:1])


#if __name__ == '__main__':
#    for arg in sys.argv[1:]:
#        if os.path.isfile(arg):
#            dump_text(arg)
#        elif os.path.isdir(arg):
#            map(dump_text, glob.glob(os.path.join(arg, '*.jpeg')) + glob.glob(os.path.join(arg, '*.JPEG')))


if __name__ == '__main__':
    for arg in sys.argv[1:]:
        if os.path.isfile(arg):
            insert_image(arg)
        elif os.path.isdir(arg):
            map(insert_image, glob.glob(os.path.join(arg, '*.jpeg')) + glob.glob(os.path.join(arg, '*.JPEG')))


















