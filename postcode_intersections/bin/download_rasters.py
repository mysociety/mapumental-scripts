#!/usr/bin/env python
"""
Downloads rasters from Mapumental for records that
have a 'url' value.
Stores files in ../rasters relative to this file.
"""
import logging
import json
import sys
import os

import requests

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logging.getLogger("requests").setLevel(logging.WARNING)
log = logging.getLogger("download_rasters")

def download_raster(record, outdir):
    filename = record['url'].split("/")[-1]
    outfile = os.path.join(outdir, filename)
    if os.path.exists(outfile):
        log.warning("File already exists for place {}, skipping download: {}".format(record['id'], outfile))
        return
    log.debug("Downloading {} for place {}".format(filename, record['id']))
    with open(outfile, "wb") as f:
        response = requests.get(record['url'], stream=True)
        if response.status_code != 200:
            log.warning("Couldn't download file for place {} from URL {}".format(record['id'], record['url']))
            response.raise_for_status()
        chunk_size = 4096
        for chunk in response.iter_content(chunk_size):
            f.write(chunk)
        record['raster_file'] = outfile

def process_data(data):
    outdir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "rasters"))
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    for record in data:
        if not record.get('url'):
            log.debug("Place {} doesn't have a url yet, skipping".format(record['id']))
            continue
        if record.get('raster_file') and os.path.exists(os.path.abspath(record['raster_file'])):
            log.debug("Place {} already has raster file: {}".format(record['id'], record['raster_file']))
            continue
        download_raster(record, outdir)
    # Quick sanity check that all records have correct URLs
    for record in (r for r in data if 'url' in r and 'raster_file' in r):
        url_filename = record['url'].split("/")[-1]
        raster_filename = record['raster_file'].split("/")[-1]
        assert url_filename == raster_filename
    no_rasters = len([r for r in data if 'raster_file' not in r])
    if no_rasters:
        log.debug("{} records haven't had their rasters downloaded yet.".format(no_rasters))
    else:
        log.debug("All records have had their rasters downloaded")
    return data


def main():
    filename = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "places.json"))
    if not os.path.exists(filename):
        print "places.json doesn't exist, bailing out"
        sys.exit(1)
    with open(filename, "rb") as f:
        data = json.load(f)
    data = process_data(data)
    with open(filename, "wb") as f:
        json.dump(data, f)

if __name__ == '__main__':
    main()
