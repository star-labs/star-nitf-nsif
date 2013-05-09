/* =========================================================================
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
 * @file test_text_write.c
 *
 * @author Carl Sandaker
 *
 * @date 9. may 2013
 *
 * @brief write a nitf 2.1 file
 *
 * @details Takes in a jpeg image and geodata, creates a correctly formatted nitf 2.1 file
 *
 *   ______    _________        _          _______
 * .' ____ \  |  _   _  |      / \        |_   __ \
 * | (___ \_| |_/ | | \_|     / _ \         | |__) |
 *  _.____`.      | |        / ___ \        |  __ /
 * | \____) | _  _| |_  _  _/ /   \ \_  _  _| |  \ \_  _
 *  \______.'(_)|_____|(_)|____| |____|(_)|____| |___|(_)
 *
 * System for Tactical Aerial Reconnaissance
 */

#include <stdio.h>
#include <string.h>

#include <import/nitf.h>

/* *********************************************************************
** This test creates a NITF from scratch with a single text segment.
** Its contents are passed in from the command line.
** ********************************************************************/

static const char* const DATE_TIME = "20120126000000";
static const char* const IGEOLO = "+37.160+067.461+37.085+069.142+36.013+069.058+36.085+067.399";

static
NITF_BOOL initializeHeader(nitf_FileHeader* header, nitf_Error* error)
{
    return (
    		nitf_Field_setString(header->fileHeader, "NITF", error) && // NITF or NSIF
            nitf_Field_setString(header->fileVersion, "02.10", error) && // 02.10 for NITF, 01.00 for NSIF
            nitf_Field_setUint32(header->complianceLevel, 3, error) && // Level of complexity required to read file
            nitf_Field_setString(header->systemType, "BF01", error) && // BF01
            nitf_Field_setString(header->originStationID, "STAR", error) && // ID of sender / creator
            nitf_Field_setString(header->fileDateTime, DATE_TIME, error) && // CCYYMMDDhhmmss, should be dynamically loaded
            nitf_Field_setString(header->fileTitle, "Text Segment Test", error) && // title of file
            nitf_Field_setString(header->classification, "U", error) && // U=Unclassified
            nitf_Field_setUint32(header->encrypted, 0, error) // 0=unencrypted, 1=encrypted
            );
}

static
NITF_BOOL initializeTextSubheader(nitf_TextSubheader* header,
                                  nitf_Error* error)
{
    return (nitf_Field_setString(header->dateTime, DATE_TIME, error) &&
            nitf_Field_setString(header->title, "Text Segment Test", error));
}

static
NITF_BOOL initializeImageSubheader(nitf_ImageSubheader* header,
								  nitf_Error* error)
{
	return (
			nitf_Field_setString(header->filePartType, "IM", error) && // Set to IM to indicate Image Subheader
			nitf_Field_setString(header->imageId, "IMA001", error) && // Image ID should be auto-incremented or dynamically loaded
			nitf_Field_setString(header->imageSecurityClass, "U", error) && // Image Security Class, U=Unclassified
			nitf_Field_setUint32(header->encrypted, 0, error) && // 0=unencrypted
			nitf_Field_setString(header->numRows, "00000768", error) && // Number of rows of pixels in the image (height)
			nitf_Field_setString(header->numCols, "00001024", error) && // Number of columns of pixels in the image (width)
			nitf_Field_setString(header->pixelValueType, "INT", error) && // Pixel value type
			nitf_Field_setString(header->imageRepresentation, "MONO", error) && // Processing required to view an image
			nitf_Field_setString(header->imageCategory, "VIS", error) && // VIS=Visual imagery
			nitf_Field_setString(header->actualBitsPerPixel, "08", error) && // Actual bits-per-pixel per band, 01-96
			nitf_Field_setString(header->pixelJustification, "R", error) && // Pixel justification, L or R
			nitf_Field_setString(header->imageLocation, IGEOLO, error) && // IGEOLO -  Image Geographic Location, approximate geographic location of image, not intended for analytical purposes +-dd.ddd+-ddd.ddd (four times) or ddmmssXdddmmssY (four times)
			nitf_Field_setUint32(header->imageComments, 0, error) && // Number of following image comments fields. 0-9.
			nitf_Field_setString(header->imageCompression, "C3", error) && // NC=image not compressed, C3=JPEG, C5=Lossless JPEG, I1=downsampled JPEG
			nitf_Field_setUint32(header->numImageBands, 1, error) && // Number of bands, corresponds to imageRepresentation field. MONO=1, RGB=3
			// start bands (1 band for monochrome, 3 bands for RGB)
			nitf_Field_setString(header->bandInfo, "M", error) && // band representation?? (i hope) M=Monochrome
			// end of bands
			nitf_Field_setString(header->imageMode, "P", error) && // B=Band Interleaved by Block, P=Band interleaved by pixel, R=Band interleaved by row, S=Band sequential - Look this up!
			nitf_Field_setUint32(header->numBlocksPerRow, 1, error) && // Number of image blocks in a row of blocks. If image consists of a single block
			nitf_Field_setUint32(header->numBlocksPerCol, 1, error) &&
			nitf_Field_setUint32(header->numPixelsPerHorizBlock, 1024, error) &&
			nitf_Field_setUint32(header->numPixelsPerVertBlock, 768, error)
	);
}

int main(int argc, char** argv)
{
    const char* outText = NULL;
    const char* outPathname = NULL;
    nitf_IOHandle outIO = NRT_INVALID_HANDLE_VALUE;
    nitf_Writer* writer = NULL;
    nitf_TextSegment* textSegment = NULL;
    nitf_SegmentWriter* textWriter = NULL;
    nitf_SegmentSource* textSource = NULL;
    nitf_Record* record = NULL;
    nitf_Error error;

    error.level = NRT_NO_ERR;

    /* Parse the command line */
    if (argc != 3)
    {
        fprintf(stderr, "Usage: %s <text to write> <output pathname>\n", argv[0]);
        return 1;
    }
    outText = argv[1];
    outPathname = argv[2];

    /* Do the work */
    outIO = nitf_IOHandle_create(outPathname,
                                 NITF_ACCESS_WRITEONLY,
                                 NITF_CREATE,
                                 &error);

    if (NITF_INVALID_HANDLE(outIO))
    {
        goto CATCH_ERROR;
    }

    writer = nitf_Writer_construct(&error);
    if (!writer)
    {
        goto CATCH_ERROR;
    }

    record = nitf_Record_construct(NITF_VER_21, &error);
    if (!record)
    {
        goto CATCH_ERROR;
    }

    if (!initializeHeader(record->header, &error))
    {
        goto CATCH_ERROR;
    }

    textSegment = nitf_Record_newTextSegment(record, &error);
    if (!textSegment)
    {
        fprintf(stderr, "new text segment failed\n");
        return 1;
    }
    if (!initializeTextSubheader(textSegment->subheader, &error))
    {
        goto CATCH_ERROR;
    }

    if (!nitf_Writer_prepare(writer, record, outIO, &error))
    {
        goto CATCH_ERROR;
    }

    textWriter = nitf_Writer_newTextWriter(writer, 0, &error);
    if (!textWriter)
    {
        goto CATCH_ERROR;
    }

    textSource = nitf_SegmentMemorySource_construct(outText,
                                                    strlen(outText),
                                                    0, 0, 0, &error);
    if (!textSource)
    {
        goto CATCH_ERROR;
    }

    if (!nitf_SegmentWriter_attachSource(textWriter, textSource, &error))
    {
        goto CATCH_ERROR;
    }

    nitf_Writer_write(writer, &error);

CATCH_ERROR:
    if (!NITF_INVALID_HANDLE(outIO))
    {
        nitf_IOHandle_close(outIO);
    }
    if (writer)
    {
        nitf_Writer_destruct(&writer);
    }

    if (error.level != NRT_NO_ERR)
    {
        nitf_Error_print(&error, stderr, "Exiting...");
        return 1;
    }

    return 0;
}
