#!/usr/bin/env python
"""
Calls the API for every record in ../places.json relative to this script.
Safe to run multiple times; API calls are only made for records that haven't
yet had a request ID stored in the JSON file.
"""
from __future__ import division

import logging
import json
import urllib
import os
import sys

import requests
import pyproj

BNG = pyproj.Proj(init="epsg:27700")
WGS = pyproj.Proj(init="epsg:4326")

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logging.getLogger("requests").setLevel(logging.WARNING)
log = logging.getLogger("call_api")


API_URL = "https://api.mapumental.com/static_map/"
DEFAULT_PARAMS = {
    'api_key': os.getenv("MAPUMENTAL_API_KEY"),
    'max_travel_time': 90,
    'time': "0830",
    'direction': "arrive_by",
    'filetype': 'arx',
    'grid_resolution': 125,
    'callback': os.getenv("MAPUMENTAL_API_CALLBACK"),
}


def pad_point(lat, lon, metres):
    """
    Returns a bounding box (w,s,e,n) that pads around a point by
    the given number of metres.
    """
    easting, northing = pyproj.transform(WGS, BNG, lon, lat)
    max_e = easting + metres
    min_e = easting - metres
    max_n = northing + metres
    min_n = northing - metres
    w, s = pyproj.transform(BNG, WGS, min_e, min_n)
    e, n = pyproj.transform(BNG, WGS, max_e, max_n)
    return (w, s, e, n)

def params_for_record(record, use_postcode=True):
    """
    Get the API params to use for an individual record.
    """
    params = DEFAULT_PARAMS.copy()
    if use_postcode:
        params['postcodes'] = record['postcode']
    else:
        params['latlons'] = ",".join((record['latitude'], record['longitude']))
    params['bounds'] = bounds_for_record(record, params['max_travel_time'])
    log.debug(params)
    return urllib.urlencode(params)

def bounds_for_record(record, max_travel_time):
    # We want to calculate the bounding box for this request automatically,
    # rather than use a fixed bounding box of, for example, the British Isles
    # that wastes time processing areas of the map that are empty.
    # Let's assume that the map should cover the area reachable by
    # moving in all directions at a constant speed from the origin point.
    # i.e., the north bound is how far you can reach by travelling due north
    # at a constant speed within the time constraints of max_travel_time.
    speed = 60 # miles per hour
    metres_per_mile = 1609.34
    metres_per_hour = speed * metres_per_mile
    total_metres = metres_per_hour * (max_travel_time / 60)
    return ",".join([str(v) for v in pad_point(record['latitude'], record['longitude'], total_metres)])

def call_api_for_record(record, use_postcode=True):
    params = params_for_record(record, use_postcode)
    response = requests.post(API_URL, data=params)
    if response.status_code != 200:
        if use_postcode:
            record['invalid_postcode'] = True
            return call_api_for_record(record, use_postcode=False)
        else:
            response.raise_for_status()
    return response.json()['map_id']


def process_data(data):
    for record in data:
        if not record.get('map_id'):
            log.debug("Sending place {} to API...".format(record['id']))
            map_id = call_api_for_record(record)
            record['map_id'] = map_id
            log.debug("...done. id: {}".format(map_id))
        else:
            log.debug("Place {} has already gone to the API, id: {}".format(record['id'], record['map_id']))
    return data


def main():
    filename = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "places.json"))
    if not os.path.exists(filename):
        print "places.json doesn't exist, bailing out"
        sys.exit(1)

    with open(filename, "rb") as f:
        data = json.load(f)
    # Process it, do API calls, store ids back in data, etc.
    data = process_data(data)
    with open(filename, "wb") as f:
        json.dump(data, f)

if __name__ == '__main__':
    main()
