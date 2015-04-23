#!/usr/bin/env python
import csv
import json
import sys
import os

"""
Converts a CSV file (specified as the first command line argument) into
a JSON file (../places.json relative to this file).
JSON format is a list of dicts, one for each row in the CSV.
The places.json file is used as a data store for subsequent processing.
Only intended to be run once as the first step of the process.
"""

def main():
    filename = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "places.json"))
    if os.path.exists(filename):
        print "places.json already exists, bailing out"
        sys.exit(1)
    with open(sys.argv[1], 'rU') as f:
        records = [r for r in csv.DictReader(f)]
    with open(filename, 'wb') as f:
        json.dump(records, f)

if __name__ == '__main__':
    main()
