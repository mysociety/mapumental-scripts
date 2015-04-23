#!/bin/sh
# Takes any number of shapefiles that have been created by make_shapefiles.py
# and writes them to the PostGIS database using shp2pgsql, deleting any rows
# that might already exist there.
# Also creates a view for simple querying of the intersections

set -eu

DB=postcode_intersections
FROMSRID=27700
SRID=4326
TABLE=public.traveltimes
COLUMN=geom

psql -d $DB -c "DROP TABLE IF EXISTS $TABLE CASCADE"

shp2pgsql -p -g $COLUMN -I -s $FROMSRID:$SRID $1 $TABLE | psql -d $DB

for i in $@; do
    shp2pgsql -a -g $COLUMN -s $FROMSRID:$SRID $i $TABLE | psql -d $DB
done

# A last bit of setup: create the view and get rid of invalid rows
psql -d $DB <<EOF
CREATE OR REPLACE VIEW intersections AS
 SELECT *, ST_Area(geom) interarea
 FROM (
  SELECT
   sectors.name sector, traveltimes.label as label, traveltimes.minutes minutes,
   ST_Area(sectors.geom) sectorarea,
   ST_Intersection(sectors.geom, traveltimes.geom) geom
  FROM sectors, traveltimes
  WHERE ST_Intersects(sectors.geom, traveltimes.geom)
  ) intersections_internal
;
DELETE FROM traveltimes WHERE minutes < 0;
EOF
