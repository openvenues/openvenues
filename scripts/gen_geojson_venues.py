import logging
import os
import subprocess
import sys
import tempfile
import urlparse
import ujson as json

from rtree.index import Index as RTreeIndex
from openvenues.extract.blacklist import *
from openvenues.format.geojson import *
from openvenues.extract.util import *

logger = logging.getLogger('geojson')

def gen_venues(d):
    for filename in os.listdir(d):
        f = open(os.path.join(d, filename))
        for line in f:
            try:
                url, data = line.split('\t', 1)
                url = json.loads(url)
                data = json.loads(data)
            except Exception:
                continue
            parsed = urlparse.urlsplit(url)
            domain = parsed.netloc
            if NON_PLACE_DOMAINS.search(domain):
                continue
            canonical = data.get('canonical')

            venues = []

            for item in data.get('items', []):
                item_type = item.get('item_type')

                props = None

                if item_type in (SCHEMA_DOT_ORG_TYPE, RDFA_TYPE):
                    props = schema_dot_org_props(item, item_type)
                elif item_type in (OG_TAG_TYPE, OG_BUSINESS_TAG_TYPE):
                    og_type = item.get('og:type', '').rsplit(':', 1)[-1].strip().lower()
                    if og_type not in OG_PLACE_TYPES and not (og_type == 'article' and OG_WHITELIST_DOMAINS.search(domain)):
                        continue
                    props = og_props(item, item_type)
                elif item_type == VCARD_TYPE:
                    props = vcard_props(item)

                if props:
                    venues.append(props)

            if venues:
                yield url, canonical, venues

def midpoint(x1, x2):
    return float(x1 + x2) / 2

def main(input_dir, output_dir):
    formatter = logging.Formatter('%(asctime)s %(levelname)s [%(name)s]: %(message)s')
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    city_names = []
    rtree = RTreeIndex()

    cities_filename = os.path.join(tempfile.gettempdir(), 'cities.json') 

    subprocess.check_call(['wget', 'https://raw.githubusercontent.com/mapzen/metroextractor-cities/master/cities.json', '-O', cities_filename])

    all_cities = json.load(open(cities_filename))

    i = 0

    for k, v in all_cities['regions'].iteritems():
       for city, data in v['cities'].iteritems():
           bbox = data['bbox']
           rtree.insert(i, (float(bbox['left']), float(bbox['bottom']), float(bbox['right']), float(bbox['top'])))        
           city_names.append(city)
           i += 1

    files = {name: open(os.path.join(output_dir, 'cities', '{}.geojson'.format(name)), 'w') for name in city_names}
    planet = open(os.path.join(output_dir, 'planet.geojson'), 'w')

    i = 0
    seen = set()

    for url, canonical, venues in gen_venues(input_dir):
        domain = urlparse.urlsplit(url).netloc.strip('www.')
        for props in venues:
            lat = props.get('latitude')
            lon = props.get('longitude')
            props['canonical'] = canonical
            props['url'] = url
            street = props.get('street_address')
            name = props.get('name')
            h = hash((name, street, lat, lon, domain))
            if lat is not None and lon is not None and h not in seen:
                cities = list(rtree.intersection((lon, lat, lon, lat)))
                if cities:
                    for c in cities:
                        f = files[city_names[c]]
                    f.write(json.dumps(venue_to_geojson(props)) + '\n')
            if h not in seen:
                planet.write(json.dumps(venue_to_geojson(props)) + '\n')
            seen.add(h)
            i += 1
            if i % 1000 == 0 and i > 0:
                logger.info('did {}'.format(i))

    logger.info('Creating manifest files')

    manifest_files = []

    for k, v in all_cities['regions'].iteritems():
        for city, data in v['cities'].iteritems():
            f = files[city]
            if f.tell() == 0:
                f.close()
                os.unlink(os.path.join(output_dir, 'cities', '{}.geojson'.format(city)))
                continue

            bbox = data['bbox']
            lat = midpoint(float(bbox['top']), float(bbox['bottom']))
            lon = midpoint(float(bbox['left']), float(bbox['right']))

            manifest_files.append({'latitude': lat, 'longitude': lon, 'file': '{}.geojson'.format(city), 'name': city.replace('_', ', ').replace('-', ' ')})

    manifest = {'files': manifest_files}

    json.dump(manifest, open(os.path.join(output_dir, 'manifest.json'), 'w'))

    logger.info('Done!')

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print 'Usage: python gen_geojson_venues.py input_dir output_dir'
        sys.exit(1)
    main(*sys.argv[1:])
