from collections import *
from openvenues.extract.util import *

def tag_value_and_attr(tag):
    value_attr = None
    value_attr = property_values.get(tag.name.lower())
    if value_attr and value_attr in tag.attrs:
        value = tag.attrs[value_attr]
    else:
        value = tag.text.strip()
    return value, value_attr

def make_links_absolute(soup, url):
    for tag in soup.find_all('a', href=True):
        tag['href'] = urlparse.urljoin(url, tag['href'])

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

    return ret        

def extract_schema_dot_org(soup, use_rdfa=False):
    items = []
    queue = deque([(None, tag) for tag in soup.find_all(True, recursive=False)])

    scope_attr = 'itemtype' if not use_rdfa else 'typeof'
    prop_attr = 'itemprop' if not use_rdfa else 'property'

    schema_type = SCHEMA_DOT_ORG_TYPE if not use_rdfa else RDFA_TYPE

    while queue:
        parent_item, tag = queue.popleft()
        if not tag.name:
            continue

        current_item = parent_item

        item = None
        prop = None
        item_scope = tag.get(scope_attr)
        item_prop = tag.get(prop_attr)
        item_type = item_scope

        if item_prop:
            prop_name = item_prop

            prop = {'name': prop_name}
            value_attr = None
            if not item_scope:
                value, value_attr = tag_value_and_attr(tag)
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
                item_type = item_type.split('/')[-1]
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
    return items

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

def extract_vcards(soup):
    items = []

    def gen_prop(name, result):
        prop = None
        if result:
            result = result[0]
            prop = {'name': name}
            value = (result.text or u'').strip()
            if value:
                prop['value'] = value
            attributes = {k: v for k, v in result.attrs.iteritems() if k not in ('class',)}
            if attributes:
                prop['attributes'] = attributes 
            if 'value' not in prop and 'attributes' not in prop:
                prop = None
        return prop


    for vcard in soup.select('.vcard'):
        item = {}
        properties = []

        address = vcard.select('.adr')
        if address: 
            have_address = False

            properties = []
            address = address[0]
            street = gen_prop('street_address', address.select('.street-address'))
            if street:
                properties.append(street)
            locality = gen_prop('locality', address.select('.locality'))
            if locality:
                properties.append(locality)
            region = gen_prop('region', address.select('.region'))
            if region:
                properties.append(region)
            postal_code = gen_prop('postal_code', address.select('.postal-code'))
            if postal_code:
                properties.append(postal_code)
            country = gen_prop('country_name', address.select('.country-name'))
            if country:
                properties.append(country)
            have_address = len(properties) > 0
            if have_address:
                org_name = gen_prop('org_name', vcard.select('.org'))
                if org_name:
                    properties.append(org_name)
                name = gen_prop('name', vcard.select('.fn')) 
                if name:
                    properties.append(name) 
                vcard_url = gen_prop('url', vcard.select('.url'))
                if vcard_url:
                    properties.append(vcard_url)
                telephone = gen_prop('telephone', vcard.select('.tel'))
                if telephone:
                    properties.append(telephone)
           
            geo = vcard.select('.geo')
            latitude = None
            longitude = None
            if geo:
                geo = geo[0]
                latitude = gen_prop('latitude', geo.select('.latitude'))
                longitude = gen_prop('longitude', geo.select('.longitude'))
            else:
                geo = vcard.select('.h-geo')
                if geo:
                    geo = geo[0]
                    latitude = gen_prop('latitude', geo.select('.p-latitude'))
                    longtitude = gen_prop('longitude', geo.select('.p-longitude'))
                
            if latitude and longitude:
                properties.append(latitude)
                properties.append(longitude)

            if properties:
                item['item_type'] = VCARD_TYPE
                item['properties'] = properties  
                items.append(item)
    return items

def extract_address_elements(soup):
    items = []

    for addr in soup.select('address'):
        items.append({'item_type': ADDRESS_ELEMENT_TYPE, 'address': BeautifulSoup(br2nl(unicode(addr))).text.strip()})

    return items

def extract_geotags(soup):

    placename = soup.select('meta[name="geo.placename"]')
    position = soup.select('meta[name="geo.position"]')
    region = soup.select('meta[name="geo.region"]')
    icbm = soup.select('meta[name="ICBM"]')
    title = soup.select('meta[name="DC.title"]')

    latitude = None
    longitude = None


    if position:
        position = position[0]
        try:
            latitude, longitude = latlon_splitter.split(position.get('content'))
        except Exception:
            pass

    if not (latitude and longitude) and icbm:
        icbm = icbm[0]
        try:
            latitude, longitude = latlon_splitter.split(icbm.get('content'))
        except Exception:
            pass

    item = {}
    if latitude and longitude:
        item['latitude'] = latitude
        item['longitude'] = longitude

    if placename:
        placename = placename[0]
        value, value_attr = tag_value_and_attr(placename)
        item['geotags.placename'] = value.strip()

    if region:
        region = region[0]
        value, value_attr = tag_value_and_attr(region)
        item['geotags.region'] = value.strip()

    return item or None

def extract_opengraph_tags(soup):
    og_attrs = {}
    for el in soup.select('meta[property^="og:"]'):
        content = el.get('content', '').strip()
        if content:
            og_attrs[el['property']] = content

    return og_attrs or None

def opengraph_item(og_tags):
    def gen_props(proplist):
        props = {}
        for prop in proplist:
            og_tag_name = 'og:{}'.format(prop)
            value = og_tags.get(og_tag_name, '').strip()

            if value:
                props[og_tag_name.replace('-', '_')] = value
        return props

    latitude_value = None
    for val in ('og:latitude', 'og:lat'):
        if val in og_tags:
            latitude_val = val

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
            return None

        if latitude and longitude:
            item['latitude'] = latitude
            item['longitude'] = longitude

    address_props = gen_props(['street-address', 'locality', 'region', 'postal-code', 'country-name', 'phone_number'])

    have_address = len(address_props) > 0
    if have_address:
        item.update(address_props)

    if have_address or have_latlon:
        title_props = gen_props(['title', 'description', 'locale', 'site_name', 'type', 'url'])
        item.update(title_props)

    return item or None

google_maps_lat_lon_path_regex = re.compile('/maps.*?@[\d]+', re.I)

def item_from_google_maps_url(url):
    query_param = 'q'
    ll_param = 'll'
    alt_ll_param = 'sll'
    near_param = 'hnear'

    latitude = None
    longitude = None

    split = urlparse.urlsplit(url)
    query_string = split.query
    path = split.path
    if query_string:
        params = urlparse.parse_qs(query_string)
        latlon = params.get(ll_param) or params.get(alt_ll_param)
        if latlon:
            try:    
                latitude, longitude = latlon_comma_splitter.split(latlon[0])
            except Exception:
                pass

        query = params.get(query_param)
        if query:
            query = query[0]

        near = params.get(near_param)
        if near:
            near = near[0]

        item = {}

        if latitude and longitude:
            item['latitude'] = latitude
            item['longitude'] = longitude

        if query:
            item['googlemaps.query'] = query
        if near:
            item['googlemaps.near'] = near
        if item:
            item['item_type'] = GOOGLE_MAP_EMBED_TYPE
            return item
    elif path and google_maps_lat_lon_path_regex.search(path):
        path_components = path.split('/')
        for p in path_components:
            if p.startswith('@'):
                values = p.strip('@').split(',')
                if len(values) >= 2:
                    latitude, longitude = []
                    try:
                        flatitude = float(latitude)
                        flongitude = float(longitude)
                    except Exception:
                        return None
                    else:
                        item = {
                            'item_type': GOOGLE_MAP_EMBED_TYPE,
                            'latitude': latitude,
                            'longitude': longitude,
                        }
                        return item
    return None


def extract_google_map_embeds(soup):
    items = []

    iframe = soup.select('iframe[src*="maps.google"]')

    if not iframe:
        iframe = soup.select('iframe[src*="google.*/maps/embed/v1/place"]')

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
    if a_tag:
        for a in a_tag:
            u = a.get('href')
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
