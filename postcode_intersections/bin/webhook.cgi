#!/usr/bin/env python
"""
This is a simple and obviously dangerous script that's intended to be used
as the 'callback' parameter to a Mapumental API request.
It reads up to 256 bytes from the request body of POST requests and writes the
data to FILENAME. It allows anyone to write arbitrary data to disk, so is
dangerous. Exercise caution if using this script.
Only intended to be made available when a number of Mapumental jobs are waiting
for completion.

To use:
  * Create the parent directory of FILENAME
  * Put this file somewhere Apache will serve it
  * Run your Mapumental API requests and watch FILENAME fill up with URLs
    as each map request is completed.
  * Make sure you remove this script when your maps have all finished!
"""
from wsgiref.handlers import CGIHandler
import os
import sys

FILENAME = os.path.expanduser("~/postcode_intersections/urls.txt")

def app(environ, start_response):
    if environ.get('REQUEST_METHOD') == 'POST':
        with open(FILENAME, 'ab') as outfile:
            print >>outfile, sys.stdin.read(256)
    start_response("200 OK", [('Content-Type','text/plain')])
    return ["OK"]


CGIHandler().run(app)
