#!/usr/bin/env python
"""
Takes any number of .arx files produced by the Mapumental API
and converts them to polyonized shapefiles - one per time threshold
(45 and 90 minutes by default)
Reads a glob or list of filenames from the commandline and writes
the shapefiles to ../shapefiles relative to this file.
"""
import os
import sys
from glob import glob

import gdal
import numpy
import osr
import ogr

THRESHOLDS = [45, 90]

@numpy.vectorize
def filter_array(i, threshold):
    if i < 0:
        return i
    if i <= threshold:
        return threshold
    return -1

def load_raster(filename):
    """
    Loads a raster file and returns its contents as a numpy array, as well
    as its transform value (i.e. its bounds and resolution etc.)
    """
    indata = gdal.Open(filename)
    inband = indata.GetRasterBand(1)
    return inband.ReadAsArray(), indata.GetGeoTransform()

def write_raster(data, filename, geotransform):
    """
    Writes a numpy array to the given filename as a GeoTIFF raster.
    """
    rows, cols = data.shape
    driver = gdal.GetDriverByName("GTiff")
    outdata = driver.Create(filename, cols, rows, 1, gdal.GDT_Float32)
    outdata.SetGeoTransform(geotransform)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(27700)
    outdata.SetProjection(srs.ExportToWkt())
    outband = outdata.GetRasterBand(1)
    outband.SetNoDataValue(-1)
    outband.WriteArray(data)
    outband.FlushCache()
    outdata.FlushCache()
    return outdata

def write_shapefile(raster, filename, layer_name="output", field_name="minutes", label=None):
    """
    Polygonizes an existing raster file and writes it to a shapefile
    """
    if os.path.isfile(filename):
        os.remove(filename)
    driver = ogr.GetDriverByName("ESRI Shapefile")
    datasource = driver.CreateDataSource(filename)
    srs = osr.SpatialReference()
    srs.ImportFromWkt(raster.GetProjectionRef())
    layer = datasource.CreateLayer(layer_name, srs=srs)
    layer.CreateField(ogr.FieldDefn(field_name, ogr.OFTInteger))
    layer.CreateField(ogr.FieldDefn("label", ogr.OFTString))
    field_id = layer.FindFieldIndex(field_name, 1)

    band = raster.GetRasterBand(1)
    gdal.Polygonize(band, None, layer, field_id, [], callback=None)
    # Strip out any features that have a -1 value, as they're unreachable
    for feature in layer:
        if feature.GetField("minutes") < 0:
            fid = feature.GetFID()
            layer.DeleteFeature(fid)
        else:
            feature.SetField("label", label)
            layer.SetFeature(feature)


def main():
    outfilename = "{filename}-filtered-{threshold}.{ext}"
    outdir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "shapefiles"))
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    outfile = os.path.join(outdir, outfilename)

    for args in sys.argv[1:]:
        for infile in glob(args):
            inarray = None
            filename = ".".join(os.path.basename(infile).split(".")[:-1])
            for threshold in THRESHOLDS:
                out_tiff = outfile.format(filename=filename, threshold=threshold, ext="tiff")
                out_shp = outfile.format(filename=filename, threshold=threshold, ext="shp")
                outdata = None
                if not os.path.exists(out_shp):
                    if not os.path.exists(out_tiff):
                        if inarray is None:
                            print "Loading {}".format(infile)
                            inarray, geotransform = load_raster(infile)
                        filtered_array = filter_array(inarray, threshold)
                        outdata = write_raster(filtered_array, out_tiff, geotransform)
                        print "Wrote {}".format(out_tiff)
                    else:
                        outdata = gdal.Open(out_tiff)
                    write_shapefile(outdata, out_shp, layer_name=filename, label=filename)
                    print "Wrote {}".format(out_shp)

if __name__ == '__main__':
    main()
