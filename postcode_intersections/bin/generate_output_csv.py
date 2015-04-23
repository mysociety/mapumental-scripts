#!/usr/bin/env python
import logging
import json
import sys
import os
import csv
from collections import defaultdict

import psycopg2
import psycopg2.extras

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("generate_output_csv")

DBNAME = "postcode_intersections"

def get_cursor():
    db = psycopg2.connect("dbname='{dbname}'".format(dbname=DBNAME))
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    return cursor

def check_data_is_valid(data, cursor):
    """
    In order for this script to run, every record in the data must have:
     * map_id
     * url
     * raster_file
    as the presence of these indicate that the preceding scripts have been run
    correctly.
    Additionally, some quick checks are performed on the database to check
    that it's got some data in it that looks roughly correct. There's no way
    to ensure that all the data is present and correct but it provides some
    level of confidence that things are as they should be.
    """
    log.debug("Checking data...")
    if not all(r.get('map_id') for r in data):
        log.error("Not all records have a 'map_id' field. Have you run call_api.py?")
        sys.exit(1)
    if not all(r.get('url') for r in data):
        log.error("Not all records have a 'url' field. Have you run add_urls.py?")
        sys.exit(1)
    if not all(r.get('raster_file') for r in data):
        log.error("Not all records have a 'raster_file' field. Have you run download_rasters.py?")
        sys.exit(1)
    log.debug("...seems OK.")

    log.debug("Checking database...")
    # Have the postcode sectors been loaded into the DB?
    cursor.execute("SELECT COUNT(*) FROM sectors")
    if cursor.fetchone()['count'] == 0:
        log.error("No postcode sectors found in the database. Please run shp2pgsql on Sectors.shp. See README for required params.")
        sys.exit(1)

    # Have the travel time shapefiles been loaded into the DB?
    cursor.execute("SELECT COUNT(*) FROM traveltimes")
    if cursor.fetchone()['count'] == 0:
        log.error("No travel time polygons found in the database. Please run import_shapefiles.sh. See README for details.")
        sys.exit(1)

    # Check that travel time polygons and sectors actually intersect.
    # If they don't, it might be due to dodgy SRIDs or indicate a deeper
    # problem in the data.
    cursor.execute("SELECT COUNT(*) FROM traveltimes, sectors WHERE sectors.geom && traveltimes.geom")
    if cursor.fetchone()['count'] == 0:
        log.error("No overlaps between travel times and postcode sectors. See README for possible causes.")
        sys.exit(1)
    log.debug("...seems OK.")

def process_data(data):
    filename = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output.csv"))
    if os.path.exists(filename):
        print "output.csv already exists, bailing out"
        sys.exit(1)
    cursor = get_cursor()
    check_data_is_valid(data, cursor)
    writer = csv.DictWriter(open(filename, "wb"), ('id', 'sector', 'reachable_in_45', 'reachable_in_90'))
    writer.writeheader()
    for record in data:
        log.debug("Working on place {}:".format(record['id']))
        log.debug("\tCalculating intersections...")
        # Using avg() is a slight abuse, but all rows being aggregated will
        # have the same value for sectorarea so it doesn't affect the
        # calculation. min() or max() would work just as well.
        query = "SELECT sector, minutes, " \
                "(sum(interarea) / avg(sectorarea))*100 as percent " \
                "FROM intersections " \
                "WHERE label = %s " \
                "GROUP BY sector, minutes " \
                "ORDER BY sector ASC"
        label = record['map_id']
        cursor.execute(query, (label, ))
        log.debug("\t...done.")

        # sectors will end up as a dict of dicts representing how
        # the percentage covered for each travel time each sector is.
        # e.g. if BA1 3 is 5.69% covered by 45 minutes and 100% covered by 90:
        # {
        #     'BA1 3': {
        #         45: 5.69,
        #         90: 100
        #     },
        #     ...
        # }
        sectors = defaultdict(dict)
        for row in cursor:
            sector = row['sector']
            sectors[sector][row['minutes']] = row['percent']
        if len(sectors) == 0:
            log.warning("\t0 sectors can reach place {} (map_id: {}).".format(record['id'], record['map_id']))
        else:
            log.debug("\t{} sector(s) can reach place {}.".format(len(sectors.keys()), record['id']))

        # Now we need to iterate across the sectors dict and write one
        # row for each to the output CSV.
        log.debug("\tWriting CSV rows...")
        for sector, coverage in sectors.items():
            percent45 = coverage.get(45, 0)
            percent90 = coverage.get(90, 0)
            # Sanity check to ensure values look right
            assert percent90 >= percent45
            assert 0 <= percent45 <= 100
            assert 0 <= percent90 <= 100
            # Write the row to the output CSV
            writer.writerow({
                'id': record['id'],
                'sector': sector,
                'reachable_in_45': percent45,
                'reachable_in_90': percent90,
            })
        log.debug("\t...done.")
        log.debug("\tFinished with place {}.".format(record['id']))

def main():
    filename = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "places.json"))
    if not os.path.exists(filename):
        print "places.json doesn't exist, bailing out"
        sys.exit(1)
    with open(filename, "rb") as f:
        data = json.load(f)
    process_data(data)

if __name__ == '__main__':
    main()
