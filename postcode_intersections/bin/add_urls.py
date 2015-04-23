#!/usr/bin/env python
import logging
import json
import sys
import os

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("add_urls")


def process_data(data, urls):
    for record in data:
        if not record.get('map_id'):
            log.debug("Place {} doesn't have a map_id yet, skipping".format(record['id']))
            continue
        if record.get('url'):
            log.debug("Place {} already has URL: {}".format(record['id'], record['url']))
            continue
        if record['map_id'] not in urls:
            log.debug("No URL yet for place: {}".format(record['id']))
            continue
        record['url'] = urls[record['map_id']]
        log.debug("Set URL for place {} to {}".format(record['id'], record['url']))
    # Quick sanity check that all records have correct URLs
    for record in (r for r in data if 'url' in r):
        map_id = record['url'].split("/")[-1].split(".")[0]
        assert map_id == record['map_id']
    no_urls = len([r for r in data if 'url' not in r])
    if no_urls:
        log.debug("Still waiting for {} API requests to finish.".format(no_urls))
    else:
        log.debug("All records have a URL, run bin/download_rasters.py")
    return data


def process_urls(urls):
    urldict = {}
    for url in urls:
        map_id = url.split("/")[-1].split(".")[0]
        urldict[map_id] = url
    return urldict


def main():
    filename = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "places.json"))
    if not os.path.exists(filename):
        print "places.json doesn't exist, bailing out"
        sys.exit(1)
    with open(filename, "rb") as f:
        data = json.load(f)

    with open(sys.argv[1], "rb") as f:
        url_lines = [l.strip() for l in f.readlines()]
    urls = process_urls(url_lines)
    data = process_data(data, urls)
    with open(filename, "wb") as f:
        json.dump(data, f)

if __name__ == '__main__':
    main()
