#!/usr/bin/env python
# -*- coding: utf-8 -*-

#******************************************************************************
#
# extract_values.py
# ---------------------------------------------------------
# Python script for extracting values of image according to
# the point shapefile.
# More: http://gis-lab.info/qa/extract-values-rasters.html
#
# Copyright (C) 2010 Alexander Bruy (alexander.bruy@gmail.com)
#               2015 Maxim Dubinin (sim@gis-lab.info)
#
# This source is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# This code is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# A copy of the GNU General Public License is available on the World Wide Web
# at <http://www.gnu.org/copyleft/gpl.html>. You can also obtain it by writing
# to the Free Software Foundation, Inc., 59 Temple Place - Suite 330, Boston,
# MA 02111-1307, USA.
#
#******************************************************************************

try:
  from osgeo import gdal, ogr, osr
except ImportError:
  import gdal, ogr, osr

import sys
import os, os.path
import time
import glob
from itertools import cycle
import math
import numpy as np

outFormat = 'ESRI Shapefile'

def mapToPixel( mX, mY, geoTransform ):
  '''Convert map coordinates to pixel coordinates.

  @param mX              Input map X coordinate (double)
  @param mY              Input map Y coordinate (double)
  @param geoTransform    Input geotransform (six doubles)
  @return pX, pY         Output coordinates (two doubles)
  '''
  if geoTransform[ 2 ] + geoTransform[ 4 ] == 0:
    pX = ( mX - geoTransform[ 0 ] ) / geoTransform[ 1 ]
    pY = ( mY - geoTransform[ 3 ] ) / geoTransform[ 5 ]
  else:
    pX, pY = applyGeoTransform( mX, mY, invertGeoTransform( geoTransform ) )
  #return int( pX + 0.5 ), int( pY + 0.5 )
  #see http://gis-lab.info/forum/viewtopic.php?f=3&t=8242&st=0&sk=t&sd=a&start=10000#p137632
  return int(math.floor(pX)), int(math.floor(pY))

def pixelToMap( pX, pY, geoTransform ):
  '''Convert pixel coordinates to map coordinates.

  @param pX              Input pixel X coordinate (double)
  @param pY              Input pixel Y coordinate (double)
  @param geoTransform    Input geotransform ( six doubles )
  @return mX, mY         Output coordinates (two doubles)
  '''
  mX, mY = applyGeoTransform( pX, pY, geoTransform )
  return mX, mY

def applyGeoTransform( inX, inY, geoTransform ):
  '''Apply a geotransform to coordinates.

  @param inX             Input coordinate (double)
  @param inY             Input coordinate (double)
  @param geoTransform    Input geotransform (six doubles)
  @return outX, outY     Output coordinates (two doubles)
  '''
  outX = geoTransform[ 0 ] + inX * geoTransform[ 1 ] + inY * geoTransform[ 2 ]
  outY = geoTransform[ 3 ] + inX * geoTransform[ 4 ] + inY * geoTransform[ 5 ]
  return outX, outY

def invertGeoTransform( geoTransform ):
  '''Invert standard 3x2 set of geotransform coefficients.

  @param geoTransform        Input GeoTransform (six doubles - unaltered)
  @return outGeoTransform    Output GeoTransform ( six doubles - updated )
                             on success, None if the equation is uninvertable
  '''
  # we assume a 3rd row that is [ 1 0 0 ]
  # compute determinate
  det = geoTransform[ 1 ] * geoTransform[ 5 ] - geoTransform[ 2 ] * geoTransform[ 4 ]

  if abs( det ) < 0.000000000000001:
    return

  invDet = 1.0 / det

  # compute adjoint and divide by determinate
  outGeoTransform = [ 0, 0, 0, 0, 0, 0 ]
  outGeoTransform[ 1 ] = geoTransform[ 5 ] * invDet
  outGeoTransform[ 4 ] = -geoTransform[ 4 ] * invDet

  outGeoTransform[ 2 ] = -geoTransform[ 2 ] * invDet
  outGeoTransfrom[ 5 ] = geoTransform[ 1 ] * invDet

  outGeoTransform[ 0 ] = ( geoTransform[ 2 ] * geoTransform[ 3 ] - geoTransform[ 0 ] * geoTransform[ 5 ] ) * invDet
  outGeoTransform[ 3 ] = ( -geoTransform[ 1 ] * geoTransform[ 3 ] + geoTransform[ 0 ] * geoTransform[ 4 ] ) * invDet

  return outGeoTransform

# =============================================================================

def usage():
  '''Show usage synopsis.
  '''
  print 'Usage: extract_values.py [-q] [-r] [-g] [-f] point_shapefile [raster_file(s)] [-d directory_with_rasters] [-rl list,of,rasters] [-e extension]'
  sys.exit( 1 )

def fileNamesToFileInfos( names ):
  '''Build fileInfo objects from list of file names.

  @param names    Input filenames (list of strings)
  @return infos   Output fileInfos (list of fileInfo objects)
  '''
  infos = []
  bandCount = 0
  for name in names:
    fi = fileInfo()
    if fi.initFromFileName( name ) == 1:
      infos.append( fi )
      bandCount += fi.bands

  return infos, bandCount

def createFields( inLayer, infos ):
  '''Add new fields according to rasters.

  @param inLayer    Input layer to add fields to (OGRLayer)
  @param infos      Input fileInfos (list of fileInfo objects)
  @return           True on success, False on any error
  '''
  for i in infos:
    if i.bands == 1:
      shortName = i.fileBaseName[ :10 ]
      fieldDef = ogr.FieldDefn( shortName, ogr.OFTReal )
      fieldDef.SetWidth( 18 )
      fieldDef.SetPrecision( 8 )
      if fields_descript: fields_csv.write(i.fileBaseName + ';' + shortName + ';1' + '\n')
      if create_csv:
        extract_csv.write(';'+i.fileBaseName)
      else:  
        if inLayer.CreateField( fieldDef ) != 0:
          print "Can't create field %s" % fieldDef.GetNameRef()
          return False
    else:
      shortName = i.fileBaseName[ :8 ]
      for b in range( i.bands ):
        fieldDef = ogr.FieldDefn( shortName + str( b + 1 ), ogr.OFTReal )
        fieldDef.SetWidth( 18 )
        fieldDef.SetPrecision( 8 )
        if fields_descript: fields_csv.write(i.fileBaseName + ';' + shortName  + str( b + 1 ) + ';' + str(b) + '\n')
        if create_csv:
          extract_csv.write(';'+i.fileBaseName + str(b))
        else:  
          if inLayer.CreateField( fieldDef ) != 0:
            print "Can't create field %s" % fieldDef.GetNameRef()
            return False
  return True

# =============================================================================

class fileInfo:
  def initFromFileName( self, fileName ):
    '''Init fileInfo object from filename.
    '''
    fh = gdal.Open( fileName )
    if fh is None:
      return 0

    self.fileName = fileName
    self.fileBaseName = os.path.splitext( os.path.basename( fileName ) )[ 0 ]
    self.extension = os.path.splitext( os.path.basename( fileName ) )[ 1 ]
    self.xSize = fh.RasterXSize
    self.ySize = fh.RasterYSize
    self.bands = fh.RasterCount
    self.geotransform = fh.GetGeoTransform()
    self.projection = osr.SpatialReference()
    self.projection.ImportFromWkt( fh.GetProjectionRef() )
    return 1

  def reportInfo( self ):
    ''' Display infrmation about fileInfo object.
    '''
    print 'Filename:', self.fileName
    print 'Bands:', self.bands

# ==============================================================================

class gdalInfo:
  '''Class to retrieve information about GDAL.
  '''
  def __init__( self ):
    self.rasterExtensions = None

  def version( self ):
    '''Get GDAL version.

    Return version of installed GDAL.
    '''
    return gdal.VersionInfo( 'RELEASE_NAME' )

  def getSupportedRasters( self ):
    '''Get list of the supported rasters.

    Return list of extensions of the supported rasters.
    '''
    if self.rasterExtensions != None:
      return self.rasterExtensions

    # first get the GDAL driver manager
    if gdal.GetDriverCount() == 0:
      gdal.AllRegister()

    self.rasterExtensions = []
    jp2Driver = None

    # for each loaded GDAL driver
    for i in range( gdal.GetDriverCount() ):
      driver = gdal.GetDriver( i )
      if driver == None:
        print 'Unable to get driver', i
        continue

      # now we need to see if the driver is for something currently
      # supported; if not, we give it a miss for the next driver
      longName = driver.LongName
      description = driver.GetDescription()
      extensions = []
      metadata = driver.GetMetadata()
      if metadata.has_key(gdal.DMD_EXTENSION):
        extensions = metadata[ gdal.DMD_EXTENSION ]

      ext = []
      if longName != '':
        if len( extensions ) > 0:
          # XXX add check for SDTS; in that case we want (*CATD.DDF)
          ext.extend( ( '*.' + extensions.replace( '/', ' *.' ) ).split( ' ' ) )

          # Add only the first JP2 driver found to the filter list (it's the one GDAL uses)
          if description == 'JPEG2000' or description.startswith( 'JP2' ): # JP2ECW, JP2KAK, JP2MrSID
            if jp2Driver != None:
              continue
            jp2Driver = driver
            ext.append( '*.j2k' )
          elif description == 'GTiff':
            ext.append( '*.tiff' )
          elif description == 'JPEG':
            ext.append( '*.jpeg' )
        else:
          # USGS DEMs use "*.dem"
          if description.startswith( 'USGSDEM' ):
            ext.append( '*.dem' )
          elif description.startswith( 'DTED' ):
            # DTED use "*.dt0"
            ext.append( '*.dt0' )
          elif description.startswith( 'MrSID' ):
            # MrSID use "*.sid"
            ext.append( '*.sid' )
          else:
            continue
      self.rasterExtensions.extend( ext )

    return list( set( self.rasterExtensions ) )

# ==============================================================================

class progressBar( object ):
  '''Class to display progress bar.
  '''
  def __init__( self, maximum, barLength ):
    '''Init progressbar instance.

    @param maximum    maximum progress value
    @param barLength  length of the bar in characters
    '''
    self.maxValue = maximum
    self.barLength = barLength
    self.spin = cycle(r'-\|/').next
    self.lastLength = 0
    self.tmpl = '%-' + str( barLength ) + 's ] %c %5.1f%%'
    sys.stdout.write( '[ ' )
    sys.stdout.flush()

  def update( self, value ):
    '''Update progressbar.

    @param value    Input new progress value
    '''
    # Remove last state.
    sys.stdout.write( '\b' * self.lastLength )

    percent = value * 100.0 / self.maxValue
    # Generate new state
    width = int( percent / 100.0 * self.barLength )
    output = self.tmpl % ( '-' * width, self.spin(), percent )

    # Show the new state and store its length.
    sys.stdout.write( output )
    sys.stdout.flush()
    self.lastLength = len( output )

# ==============================================================================

if __name__ == '__main__':
  inRasters = []
  rasterPath = None
  inShapeName = None
  ext = None
  needTransform = False
  gdalalloc = False
  fields_descript = False
  create_csv = False
  rasterPaths2 = None
  quiet = False
  
  gdal.AllRegister()

  formats = gdalInfo().getSupportedRasters()
###  print formats
  
  args = gdal.GeneralCmdLineProcessor( sys.argv )

  if args is None or len( args ) < 2:
    usage()

  # parse command line arguments
  i = 1
  while i < len( args ):
    arg = args[ i ]
    if arg == '-r':
      needTransform = True
    elif arg == '-g':
      gdalalloc = True
    elif arg == '-q':
      quiet = True
    elif arg == '-f':
      fields_descript = True
    elif arg == '-c':
      create_csv = True  
    elif arg == '-rl':
        inRasters.extend( args[ i + 1].split(',') )
    elif arg == '-d':
      i += 1
      rasterPaths = args[ i ]
      rasterPaths2 = []
      for rasterPath in rasterPaths.split(','):
          if os.path.exists( rasterPath ) == False:
            print( 'Directory '  + rasterPath + ' does not exist' )
          if rasterPath[ len( rasterPath ) - 1 : ] != os.sep:
            rasterPath = rasterPath + os.sep
          rasterPaths2.append(rasterPath)
      if len(rasterPaths2) == 0:
        sys.exit( 1 )
    elif arg == '-e':
        i += 1
        ext = args[ i ]
    elif inShapeName is None:
      inShapeName = arg
    elif arg != '-d' and arg != '-rl':
      inRasters.append(args[i])
    i += 1
  
  if not quiet: print 'Found GDAL version:', gdalInfo().version(), '\n'
  
  if inShapeName is None:
    print("No point shapefile was specified. Nothing to do.")
    sys.exit( 1 )
  
  if fields_descript: 
    fields_csv = open(inShapeName.replace('.shp','_fields.csv'),'wb')
    fields_csv.write('RASTER;NEWFIELD;BAND\n')

  if create_csv: 
    extract_csv = open(inShapeName.replace('.shp','_extract.csv'),'wb')

  #-d is set
  if rasterPaths2 is not None:
    if ext is not None:
        for rasterPaths in rasterPaths2:
            f = '*.' + ext
            if f not in formats:
                print 'Raster extension (%s) is not supported'%ext
                sys.exit( 1 )
            files = glob.glob( rasterPath + f )
            inRasters.extend( files )
    else:
        for rasterPaths in rasterPaths2:
            for f in formats:
              # look for supported rasters in directory
              files = glob.glob( rasterPath + f )
              inRasters.extend( files )

  if len( inRasters ) == 0:
    print 'No input rasters selected.'
    usage()

  # convert filenames to fileinfos
  fileInfos, bands = fileNamesToFileInfos( inRasters )

  # try to open source shapefile
  if int(gdal.VersionInfo()) > 1990000:
    inShape = ogr.Open( inShapeName, gdal.OF_VECTOR )
  else:
    inShape = ogr.Open( inShapeName, 1 )
  if inShape is None:
    print 'Unable to open shapefile', inShapeName
    sys.exit( 1 )

  inLayer = inShape.GetLayer( 0 )
  if fields_descript: 
    layerDefinition = inLayer.GetLayerDefn()
    for i in range(layerDefinition.GetFieldCount()):
         fields_csv.write(layerDefinition.GetFieldDefn(i).GetName() + ';' + layerDefinition.GetFieldDefn(i).GetName() + ';1\n')

  if create_csv:
    extract_csv.write('FID')    
  featCount = inLayer.GetFeatureCount()
  layerCRS = inLayer.GetSpatialRef()

  # add new fields to the shapefile
  createFields( inLayer, fileInfos )

  # init progressbar
  if gdalalloc:
    max = featCount * len(inRasters)
  else:
    max = featCount * bands
  if not quiet: pb = progressBar( max + 1, 65 )
  i = 0
  start = time.time()
  # process points and rasters
  fi = 0
  if create_csv:
    arExt=np.zeros((featCount,len(fileInfos)+1))
  for f in fileInfos:
    fi += 1
    i += 1
    if not quiet: pb.update( i )
    gt = f.geotransform
    rasterCRS = f.projection
    #print "Layer", layerCRS.ExportToWkt()
    #print "Raster", rasterCRS.ExportToWkt()
    if needTransform:
      coordTransform = osr.CoordinateTransformation( layerCRS, rasterCRS )
      if coordTransform is None and needTransform:
        print 'Error while creating coordinate transformation.'
        sys.exit( 1 )
    if not gdalalloc:
        ds = gdal.Open( f.fileName )
    if f.bands == 1:
      shortName = f.fileBaseName[ :10 ]
      if not gdalalloc:
        band = ds.ReadAsArray()
      inLayer.ResetReading()
      inFeat = inLayer.GetNextFeature()
      while inFeat is not None:
        i += 1
        if not quiet: pb.update( i )
        geom = inFeat.GetGeometryRef()
        x = geom.GetX()
        y = geom.GetY()
        #print "BEFORE", x, y
        if needTransform:
          res = coordTransform.TransformPoint( x, y, 0 )
          x = res[ 0 ]
          y = res[ 1 ]
        rX, rY = mapToPixel( x, y, gt )
        if rX > f.xSize or rY > f.ySize:
          inFeat = inLayer.GetNextFeature()
          continue
        if gdalalloc:
            value = os.popen('gdallocationinfo -valonly -wgs84 %s %s %s' % (f.fileName, x, y)).read()
        else:
            value = band[ rY, rX ]
        if create_csv:
          arExt[inFeat.GetFID(),0]=inFeat.GetFID()
          arExt[inFeat.GetFID(),fi]=value
        else:    
          inFeat.SetField( shortName, float(value) )
          if inLayer.SetFeature( inFeat ) != 0:
            print 'Failed to update feature.'
            sys.exit( 1 )

        inFeat = inLayer.GetNextFeature()
    else:
      shortName = f.fileBaseName[ :8 ]
      inLayer.ResetReading()
      inFeat = inLayer.GetNextFeature()
      while inFeat is not None:
        i += 1
        if not quiet: pb.update( i )
        geom = inFeat.GetGeometryRef()
        x = geom.GetX()
        y = geom.GetY()
        if needTransform:
          res = coordTransform.TransformPoint( x, y, 0 )
          x = res[ 0 ]
          y = res[ 1 ]
        rX, rY = mapToPixel( x, y, gt )
        if rX > f.xSize or rY > f.ySize:
          inFeat = inLayer.GetNextFeature()
          continue
        if gdalalloc:
          #TODO: check that raster has CRS assigned
          values = os.popen('gdallocationinfo -valonly -wgs84 %s %s %s' % (f.fileName, x, y)).read().split('\n')
          values = [v.replace('.#IND', '') for v in values]
          for b in range( f.bands ):
            if create_csv:
              arExt[inFeat.GetFID(),0]=inFeat.GetFID()
              arExt[inFeat.GetFID(),fi]=float(values[b])
            else:
              inFeat.SetField( shortName + str( b + 1 ), float(values[b]) )
              if inLayer.SetFeature( inFeat ) != 0:
                print 'Failed to update feature.'
                sys.exit( 1 )
        else:
          for b in range( f.bands ):
            rband = ds.GetRasterBand( b + 1 )
            band = rband.ReadAsArray()
            value = band[ rY, rX ]
            rband = None
            if create_csv:
              arExt[inFeat.GetFID(),0]=inFeat.GetFID()
              arExt[inFeat.GetFID(),fi]=value
            else:
              inFeat.SetField( shortName + str( b + 1 ), float(value) )
              if inLayer.SetFeature( inFeat ) != 0:
                print 'Failed to update feature.'
                sys.exit( 1 )
        inFeat = inLayer.GetNextFeature()
    ds = None

  if create_csv:
    for r in range(featCount):
      extract_csv.write('\n')
      extract_csv.write(str(arExt[r,0])+';')
      for c in range(1,fi):
        extract_csv.write(str(arExt[r,c])+';')
      extract_csv.write(str(arExt[r,fi]))
  if not quiet: print '\nCompleted in', time.time() - start, 'sec.'
