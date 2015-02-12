import logging
import traceback
import ujson as json

from collections import *
from itertools import chain
from bs4 import BeautifulSoup, SoupStrainer
from openvenues.extract.util import *


logger = logging.getLogger('extract.soup')


def tag_value_and_attr(tag):
    value_attr = None
    value_attr = property_values.get(tag.name.lower())
    if value_attr and value_attr in tag.attrs:
        value = tag.attrs[value_attr]
    else:
        value = tag.text.strip()
    return value, value_attr


def extract_links(soup):
    def not_nofollow(rel):
        return rel != 'nofollow'

    for tag in soup.find_all('a', attrs={'href': True,
                                         'rel': not_nofollow}):
        link = tag['href']
        # Make link absolute
        link = urlparse.urljoin(url, link)
        yield link


def extract_basic_metadata(soup):
    title_tags = soup.select('meta[property="og:title"]') + soup.select('meta[name="title"]') + soup.find_all('title')
    title = None
    for t in title_tags:
        value, value_attr = tag_value_and_attr(t)
        if value and value.strip():
            title = value.strip()
            break

    if not title:
        return None

    ret = {'title': title}

    description_tags = soup.select('meta[property="og:description"]') or soup.select('meta[name="description"]')
    if description_tags:
        for d in description_tags:
            value, value_attr = tag_value_and_attr(d)
            if value and value.strip():
                description = value.strip()
                ret['description'] = description
                break

    canonical = soup.select('link[rel="canonical"]')
    if canonical and canonical[0].get('href'):
        ret['canonical'] = canonical[0]['href']

    alternates = soup.select('link[rel="alternate"]')
    if alternates:
        ret['alternates'] = [{'link': tag['href'],
                              'lang': tag.get('hreflang')
                              } for tag in alternates if tag.get('href')]

    rel_tag = soup.select('[rel="tag"]')
    if rel_tag:
        all_tags = []
        for t in rel_tag:
            tag = {}
            value = t.text.strip()
            if value:
                tag['value'] = value
            link, link_attr = tag_value_and_attr(t)
            if link_attr and value:
                tag['link'] = link_attr
                tag['link_value'] = link
            elif link_attr:
                tag['value'] = link
                tag['attr'] = link_attr
            else:
                continue
            all_tags.append(tag)

        ret['tags'] = all_tags

    return ret


street_props = set(['street_address', 'street', 'address', 'street-address', 'streetaddress'])
latlon_props = set(['latitude', 'longitude', 'lat', 'lon', 'long'])


def extract_schema_dot_org(soup, use_rdfa=False):
    items = []

    scope_attr = 'itemtype'
    prop_attr = 'itemprop'

    schema_type = SCHEMA_DOT_ORG_TYPE if not use_rdfa else RDFA_TYPE

    xmlns = None

    if use_rdfa:
        data_vocabulary = None
        # Verify that we have xmlns defined
        for tag in soup.find_all(True):
            data_vocabulary = [k for k, v in tag.attrs.iteritems()
                               if k.startswith('xmlns:') and 'data-vocabulary' in v]
            if data_vocabulary:
                data_vocabulary = data_vocabulary[0]
                break
        if not data_vocabulary:
            return items
        else:
            xmlns = data_vocabulary.split(':', 1)[-1]

    queue = deque([(None, tag) for tag in soup.find_all(True, recursive=False)])

    have_street = False
    have_latlon = False

    while queue:
        parent_item, tag = queue.popleft()
        if not tag.name:
            continue

        current_item = parent_item

        item = None
        prop = None

        has_vocab = False
        item_scope = tag.get(scope_attr)

        if not item_scope and use_rdfa:
            item_scope = tag.get('typeof', tag.get('vocab'))
            if not item_scope or not item_scope.startswith('{}:'.format(xmlns)):
                item_scope = None

        item_prop = tag.get(prop_attr)
        item_type = item_scope

        if not item_prop and use_rdfa:
            item_prop = tag.get('property')
            if not item_prop or not item_prop.startswith('{}:'.format(xmlns)):
                item_prop = tag.get('rel', [])
                item_prop = [p for p in item_prop if p.startswith('{}:'.format(xmlns))]
                if not item_prop:
                    item_prop = None
                else:
                    item_prop = item_prop[0]

        if item_prop:
            prop_name = item_prop
            if use_rdfa:
                prop_name = prop_name.split(':', 1)[-1]

            prop_name = prop_name.replace('-', '_')

            prop = {'name': prop_name}
            value_attr = None
            if not item_scope:
                value, value_attr = tag_value_and_attr(tag)
                if use_rdfa and not value and tag.get('content'):
                    value, value_attr = tag['content'], 'content'

                prop['value'] = value
            attributes = {k: v for k, v in tag.attrs.iteritems() if k not in (scope_attr, prop_attr)}
            if value_attr:
                prop['text'] = tag.text.strip()
                prop['value_attr'] = value_attr 

            if attributes:
                prop['attributes'] = attributes
            if current_item is not None:
                current_item['properties'] = current_item['properties'] or []
                current_item['properties'].append(prop)

        if item_scope:
            if prop is not None:
                item = prop
            else:
                item = {}
            is_place_item = False
            if item_type:
                if not use_rdfa:
                    item_type = item_type.split('/')[-1]
                elif use_rdfa and xmlns and item_type.startswith('{}:'.format(xmlns)):
                    item_type = item_type.split(':', 1)[-1]
                is_place_item = item_type.lower() in PLACE_SCHEMA_TYPES

            item.update({
                'item_type': schema_type,
                'type': item_type,
            })
            item['properties'] = []

            if is_place_item:
                items.append(item)

            current_item = item

        queue.extend([(current_item, child) for child in tag.find_all(True, recursive=False)])

    ret = []

    for item in items:
        have_street = False
        have_latlon = False
        item_type = item.get('item_type')
        if item_type == 'schema.org':
            for prop in item.get('properties', []):
                name = prop.get('name', '').lower()
                if name == 'address':
                    props = set([p.get('name') for p in prop.get('properties', [])])
                    if props & street_props:
                        have_street = True
                elif name.lower() == 'streetaddress':
                    have_street = True
                if name == 'geo':
                    props = set([p.get('name') for p in prop.get('properties', [])])
                    if len(latlon_props & props) == 2:
                        have_latlon = True
                if name in latlon_props:
                    have_latlon = True
                if name in street_props:
                    have_street = True
        elif item_type == 'rdfa':
            props = set([p.get('name', '').lower() for p in item.get('properties', [])])

            have_street = props & street_props
            have_latlon = len(props & latlon_props) >= 2
        if have_street or have_latlon:
            ret.append(item)

    return ret

FACEBOOK = 'facebook'
TWITTER = 'twitter'
INSTAGRAM = 'instagram'
PINTEREST = 'pinterest'
YELP = 'yelp'
FOURSQUARE = 'foursquare'
GOOGLE_PLUS = 'google_plus'
YOUTUBE = 'youtube'
VIMEO = 'vimeo'


social_href_patterns = {
    'facebook.com': FACEBOOK,
    'twitter.com': TWITTER,
    'instagram.com': INSTAGRAM,
    'pinterest.com': PINTEREST,
    'yelp.': YELP,
    'foursquare': FOURSQUARE,
    'plus.google': GOOGLE_PLUS,
    'youtube': YOUTUBE,
    'youtu.be': YOUTUBE,
    'vimeo.com': VIMEO,

}


def extract_social_handles(soup):
    max_matches = 0
    ids = defaultdict(list)
    for pattern, site in social_href_patterns.iteritems():
        matches = soup.select(u'a[href*="{}"]'.format(pattern))
        if len(matches) > max_matches:
            max_matches = len(matches)
        for m in matches:
            value, value_attr = tag_value_and_attr(m)
            ids[site].append(value)
    return dict(ids)


value_attr_regex = re.compile("value-.*")

def extract_vcards(soup):
    items = []

    def gen_prop(name, selector):
        prop = None
        if selector:
            result = selector[0]
            prop = {'name': name}
            val_select = result.select('.value')
            if val_select:
                value, value_attr = tag_value_and_attr(val_select[0])
            else:
                val_select = result.find_all(class_=value_attr_regex)
                if not val_select:
                    value, value_attr = tag_value_and_attr(result)
                else:
                    value_attr = val_select[0].attrs['class'][0].split('-', 1)[-1]
                    value = val_select[0].attrs.get(value_attr)
                    if not value:
                        value, value_attr = tag_value_and_attr(result)

            text = (result.text or u'').strip()
            if not value_attr:
                prop['value'] = text
            else:
                prop['text'] = text
                prop['value'] = value
                prop['value_attr'] = value_attr

            attributes = {k: v for k, v in result.attrs.iteritems() if k not in ('class', value_attr)}
            if attributes:
                prop['attributes'] = attributes 
            if 'text' not in prop and 'value' not in prop and 'attributes' not in prop:
                prop = None
        return prop

    vcards = soup.select('.vcard')
    if not vcards:
        vcards = soup.select('.adr')

    for vcard in vcards:
        item = {}
        properties = []
        have_address = False

        street = gen_prop('street_address', vcard.select('.street-address'))
        if street:
            properties.append(street)
            have_address = True
        locality = gen_prop('locality', vcard.select('.locality'))
        if locality:
            properties.append(locality)
        region = gen_prop('region', vcard.select('.region'))
        if region:
            properties.append(region)
        postal_code = gen_prop('postal_code', vcard.select('.postal-code'))
        if postal_code:
            properties.append(postal_code)
        country = gen_prop('country', vcard.select('.country-name'))
        if country:
            properties.append(country)

        have_latlon = False

        latitude = gen_prop('latitude', vcard.select('.latitude'))
        longitude = gen_prop('longitude', vcard.select('.longitude'))
        if not latitude and longitude:
            latitude = gen_prop('latitude', vcard.select('.p-latitude'))
            longtitude = gen_prop('longitude', vcard.select('.p-longitude'))
        
        if latitude and longitude:
            properties.append(latitude)
            properties.append(longitude)
            have_latlon = True

        if have_address or have_latlon:
            org_name = gen_prop('org_name', vcard.select('.org'))
            if org_name:
                properties.append(org_name)
            name = gen_prop('name', vcard.select('.fn'))
            if name:
                properties.append(name)
            photo = gen_prop('photo', vcard.select('.photo'))
            if photo:
                properties.append(photo)
            vcard_url = gen_prop('url', vcard.select('.url a'))
            if not vcard_url:
                vcard_url = gen_prop('url', vcard.select('a.url'))
            if vcard_url:
                properties.append(vcard_url)
            telephone = gen_prop('telephone', vcard.select('.tel'))
            if telephone:
                properties.append(telephone)
            category = gen_prop('category', vcard.select('.category'))
            if category:
                properties.append(category)
        else:
            continue

        if properties:
            item['item_type'] = VCARD_TYPE
            item['properties'] = properties  
            items.append(item)
    return items


def extract_address_elements(soup):
    items = []

    for addr in soup.select('address'):
        html = unicode(addr)
        items.append({'item_type': ADDRESS_ELEMENT_TYPE, 'address': BeautifulSoup(html).text.strip(),
            'original_html': html})
    return items


def extract_geotags(soup):
    placename = soup.select('meta[name="geo.placename"]')
    position = soup.select('meta[name="geo.position"]')
    region = soup.select('meta[name="geo.region"]')
    icbm = soup.select('meta[name="ICBM"]')
    title = soup.select('meta[name="DC.title"]')

    item = {}

    if position:
        position = position[0]
        value, value_attr = tag_value_and_attr(position)
        if value and value.strip():
            item['geotags.position'] = value.strip()

    if not position and icbm:
        icbm = icbm[0]
        value, value_attr = tag_value_and_attr(icbm)
        if value and value.strip():
            item['geotags.icbm'] = value.strip()

    if placename:
        placename = placename[0]
        value, value_attr = tag_value_and_attr(placename)
        if value:
            item['geotags.placename'] = value.strip()

    if region:
        region = region[0]
        value, value_attr = tag_value_and_attr(region)
        if value:
            item['geotags.region'] = value.strip()

    if title:
        title = title[0]
        value, value_attr = tag_value_and_attr(title)
        if value:
            item['geotags.title'] = value.strip()

    if item:
        item['item_type'] = GEOTAG_TYPE


    return item or None


def extract_opengraph_tags(soup):
    og_attrs = {}
    for el in soup.select('meta[property^="og:"]'):
        content = el.get('content', '').strip()
        if content:
            og_attrs[el['property']] = content

    return og_attrs or None


def extract_opengraph_business_tags(soup):
    og_attrs = {}
    for el in soup.select('meta[property^="business:"]'):
        content = el.get('content', '').strip()
        if content:
            og_attrs[el['property']] = content

    for el in soup.select('meta[property^="place:"]'):
        content = el.get('content', '').strip()
        if content:
            og_attrs[el['property']] = content

    return og_attrs or None


def gen_og_props(og_tags, proplist, prefix='og'):
    props = {}
    for prop in proplist:
        og_tag_name = '{}:{}'.format(prefix, prop)
        value = og_tags.get(og_tag_name, '').strip()

        if value:
            props[og_tag_name] = value
    return props


def opengraph_item(og_tags):
    latitude_value = None
    for val in ('og:latitude', 'og:lat'):
        if val in og_tags:
            latitude_value = val

    longitude_value = None
    for val in ('og:longitude', 'og:lng'):
        if val in og_tags:
            longitude_value = val

    have_latlon = latitude_value and longitude_value

    item = {}
    if have_latlon:
        try:
            latitude = og_tags[latitude_value].strip()
            longitude = og_tags[longitude_value].strip()

        except Exception:
            logger.error('Error in opengraph tags extracting lat/lon: {}'.format(traceback.format_exc()))

        if latitude and longitude:
            item['og:latitude'] = latitude
            item['og:longitude'] = longitude

    address_props = gen_og_props(og_tags, ['street-address', 'locality', 'region', 'postal-code', 'country-name', 'phone_number'])

    have_address = len(address_props) > 0
    if have_address:
        item.update(address_props)

    if have_address or have_latlon:
        item['item_type'] = OG_TAG_TYPE
        title_props = gen_og_props(og_tags, ['title', 'description', 'locale', 'site_name', 'type', 'url'])
        item.update(title_props)

    return item or None


def opengraph_business(og_tags):
    item = {}

    address_props = gen_og_props(og_tags, ['street_address', 'locality', 'region', 'postal_code',
                                  'country', 'phone_number', 'website'], prefix='business:contact_data')

    have_address = len(address_props) > 0
    if have_address:
        item.update(address_props)

    latitude = og_tags.get('place:location:latitude', '').strip()
    longitude = og_tags.get('place:location:longitude', '').strip()

    have_latlon = latitude and longitude
    if have_latlon:
        item['place:location:latitude'] = latitude
        item['place:location:longitude'] = longitude

    if have_address or have_latlon:
        item['item_type'] = OG_BUSINESS_TAG_TYPE
        title_props = gen_og_props(og_tags, ['title', 'description', 'locale', 'site_name', 'type', 'url'])
        item.update(title_props)

    return item or None


google_maps_lat_lon_path_regex = re.compile('/maps.*?@[\d]+', re.I)


def item_from_google_maps_url(url):
    query_param = 'q'

    ll_param_names = ('ll', 'sll', 'center')
    ll_param = 'll'
    alt_ll_param = 'sll'

    near_param_names = ('hnear', 'near')
    daddr_param = 'daddr'

    latitude = None
    longitude = None

    split = urlparse.urlsplit(url)
    query_string = split.query
    path = split.path
    if query_string:
        params = urlparse.parse_qs(query_string)
        for param in ll_param_names:
            latlon = params.get(param)
            try:
                latitude, longitude = latlon_comma_splitter.split(latlon[0])
                if not latitude and longitude:
                    continue
            except Exception:
                continue

        query = params.get(query_param)
        if query:
            query = query[0]

        for param in near_param_names:
            near = params.get(near_param)
            if near:
                near = near[0]
                break

        daddr = params.get(daddr_param)
        if daddr:
            daddr = daddr[0]

        item = {}

        if latitude and longitude:
            item['latitude'] = latitude
            item['longitude'] = longitude

        if query:
            item['googlemaps.query'] = query
        if near:
            item['googlemaps.near'] = near
        if daddr:
            item['googlemaps.daddr'] = daddr
        if item:
            item['googlemaps.url'] = url
            item['item_type'] = GOOGLE_MAP_EMBED_TYPE
            return item
    
    if path and google_maps_lat_lon_path_regex.search(path):
        path_components = path.split('/')
        for p in path_components:
            if p.startswith('@'):
                values = p.strip('@').split(',')
                if len(values) >= 2:
                    latitude, longitude = values[:2]
                    if latitude and longitude:
                        item = {
                            'item_type': GOOGLE_MAP_EMBED_TYPE,
                            'latitude': latitude,
                            'longitude': longitude,
                        }
                        return item
    return None


google_maps_href_regex = re.compile('google\.[^/]+\/maps')
google_maps_embed_regex = re.compile('google\.[^/]+\/maps/embed/.*/place')


def extract_google_map_embeds(soup):
    items = []

    iframe = soup.select('iframe[src*="maps.google"]')

    if not iframe:
        iframe = soup.find_all('iframe', src=google_maps_embed_regex)

    seen = set()

    if iframe:
        for f in iframe:
            u = f.get('src')
            if u not in seen:
                item = item_from_google_maps_url(u)
                if item:
                    items.append(item)
                seen.add(u)

    a_tag = soup.select('a[href*="maps.google"]')
    if not a_tag:
        a_tag = soup.find_all('a', href=google_maps_href_regex)
    if a_tag:
        for a in a_tag:
            u = a.get('href')
            if u not in seen:
                item = item_from_google_maps_url(u)
                if item:
                    items.append(item)
                seen.add(u)

    static_maps = soup.select('img[src*="maps.google"]')
    if static_maps:
        for img in static_maps:
            u = img.get('src')
            if u not in seen:
                item = item_from_google_maps_url(u)
                if item:
                    items.append(item)
                seen.add(u)

    shortener_a_tag = soup.select('a[href*="goo.gl/maps"]')
    if shortener_a_tag:
        for a in a_tag:
            u = a.get('href')
            if u not in seen:
                text = (a.text or '').strip()
                item = {
                    'item_type': GOOGLE_MAP_SHORTENED,
                    'url': u,
                }
                if text:
                    item['anchor'] = text
                items.append(item)
                seen.add(u)

    return items


def extract_data_lat_lon_attributes(soup):
    lat = soup.find_all(attrs={'data-lat': True})
    items = []
    for tag in lat:
        latitude = tag['data-lat'].strip()

        longitude = tag.get('data-lng', tag.get('data-lon', tag.get('data-long', None)))

        if latitude and longitude:
            items.append({'item_type': DATA_LATLON_TYPE,
                          'latitude': latitude,
                          'longitude': longitude,
                          'attrs': tag.attrs
                          })

    return items


hopstop_route_regex = re.compile('hopstop\.[^/]+/route')
hopstop_map_regex = re.compile('hopstop\.[^/]+/map')

def extract_hopstop_direction_embeds(soup):
    hopstop_embeds = soup.find_all('a', href=hopstop_route_regex)
    items = []
    for tag in hopstop_embeds:
        split = urlparse.urlsplit(tag.attrs['href'])
        query_string = split.query
        if query_string:
            params = urlparse.parse_qs(query_string)
            if params and 'address2' in params and 'zip2' in params:
                item = {'item_type': HOPSTOP_ROUTE_TYPE,
                        'address': params['address2'][0],
                        'postal_code': params['zip2'][0]
                        }
                items.append(item)
    return items


def extract_hopstop_map_embeds(soup):
    hopstop_embeds = soup.find_all('a', href=hopstop_map_regex)
    items = []
    for tag in hopstop_embeds:
        split = urlparse.urlsplit(tag.attrs['href'])
        query_string = split.query
        if query_string:
            params = urlparse.parse_qs(query_string)
            if params and 'address' in params:
                item = {'item_type': HOPSTOP_MAP_TYPE,
                        'address': params['address'][0]}
                items.append(item)
    return items


# Some big sites like yellowpages.com use this
def extract_mappoint_embeds(soup):
    pushpins = soup.find_all(attrs={'data-pushpin': True})
    items = []
    if len(pushpins) == 1:
        try:
            item = json.loads(pushpins[0]['data-pushpin'])
            latitude = item.get('lat', item.get('latitude'))
            longitude = item.get('lon', item.get('long', item.get('longitude')))
            if latitude and longitude:
                return [{'item_type': MAPPOINT_EMBED_TYPE,
                         'mappoint.latitude': latitude,
                         'mappoint.longitude': longitude}]
        except Exception:
            logger.error('Error in extracting mappoint embed: {}'.format(traceback.format_exc()))
            return []



def extract_items(soup):
    items = []

    schema_dot_org_items = extract_schema_dot_org(soup)
    rdfa_items = extract_schema_dot_org(soup, use_rdfa=True)
    vcards = extract_vcards(soup)
    address_elements = extract_address_elements(soup)
    opengraph_tags = extract_opengraph_tags(soup)
    opengraph_business_tags = extract_opengraph_business_tags(soup)
    google_maps_embeds = extract_google_map_embeds(soup)
    geotags = extract_geotags(soup)

    mappoint_pushpins = extract_mappoint_embeds(soup)
    hopstop_route_embeds = extract_hopstop_direction_embeds(soup)
    hopstop_map_embeds = extract_hopstop_map_embeds(soup)

    data_latlon_attrs = extract_data_lat_lon_attributes(soup)

    if geotags:
        geotags = [geotags]

    basic_metadata = extract_basic_metadata(soup)

    items = list(chain(*(c for c in (schema_dot_org_items,
                                     rdfa_items,
                                     vcards,
                                     address_elements,
                                     geotags,
                                     google_maps_embeds,
                                     mappoint_pushpins,
                                     hopstop_route_embeds,
                                     hopstop_map_embeds,
                                     data_latlon_attrs) if c)))
    if opengraph_tags:
        i = opengraph_item(opengraph_tags)
        if i:
            items.append(i)

    if opengraph_business_tags:
        i = opengraph_business(opengraph_business_tags)
        if i:
            items.append(i)

    social_handles = extract_social_handles(soup)

    ret = {}
    if items:
        ret['items'] = items

        if social_handles:
            ret['social'] = social_handles

        if opengraph_tags:
            ret['og'] = opengraph_tags

        if basic_metadata:
            ret.update(basic_metadata)

        return ret

