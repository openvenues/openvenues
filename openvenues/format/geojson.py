import re

from openvenues.utils.encoding import *
from openvenues.extract.blacklist import *
from openvenues.extract.util import *

SCHEMA_DOT_ORG_IGNORE_FIELDS = set([
    'events',
    'makesoffer',
])

field_map = {
    'alternatename': 'alternate_name',
    'legalname': 'legal_name',

    'street': 'street_address',
    'street-address': 'street',
    'street_name': 'street_address',
    'streetaddress': 'street_address',

    'city': 'locality',
    'municipality': 'locality',
    'addresslocality': 'locality',
    'address-locality': 'locality',

    'neighbourhood': 'neighborhood',

    'state': 'region',
    'state_code': 'region',
    'province': 'region',
    'addressregion': 'region',
    'address-region': 'region',

    'postal': 'postal_code',
    'post': 'postal_code',
    'postcode': 'postal_code',
    'postalcode': 'postal_code',
    'zip': 'postal_code',
    'zipcode': 'postal_code',
    'zip_code': 'postal_code',

    'pobox': 'po_box',
    'postofficeboxnumber': 'po_box',

    'addresscountry': 'country',
    'country-name': 'country',
    'country_name': 'country',
    'countryname': 'country',

    'containedin': 'contained_in',
    'sameas': 'same_as',

    'phone': 'telephone',
    'tel': 'telephone',

    'category_name': 'category',
    'additionaltype': 'additional_type',

    'faxnumber': 'fax',

    'tickersymbol': 'ticker_symbol',
    'taxid': 'tax_id',
    'vatnumber': 'vat_number',

    'openinghours': 'hours',
    'openinghoursspecification': 'hours_specification',
    'pricerange': 'price_range',
    'servescuisine': 'cuisine',
    'currenciesaccepted': 'currencies_accepted',
    'paymentaccepted': 'payment_methods',
    'branchof': 'branch_of',
    'foundingdate': 'founding_date',
    'acceptsreservations': 'accepts_reservations',
    'medicalspecialty': 'medical_specialty',

    'reviewcount': 'review_count',
    'ratingcount': 'rating_count',
    'ratingvalue': 'rating_value',

}

beginning_re = re.compile('^[^0-9\-]+', re.UNICODE)
end_re = re.compile('[^0-9]+$', re.UNICODE)

latitude_dms_regex = re.compile(ur'^(-?[0-9]{1,2})[ ]*[ :°ºd][ ]*([0-5]?[0-9])?[ ]*[:\'\u2032m]?[ ]*([0-5]?[0-9](?:\.\d+)?)?[ ]*[:\?\"\u2033s]?[ ]*(N|n|S|s)?$', re.I | re.UNICODE)
longitude_dms_regex = re.compile(ur'^(-?1[0-8][0-9]|0?[0-9]{1,2})[ ]*[ :°ºd][ ]*([0-5]?[0-9])?[ ]*[:\'\u2032m]?[ ]*([0-5]?[0-9](?:\.\d+)?)?[ ]*[:\?\"\u2033s]?[ ]*(E|e|W|w)?$', re.I | re.UNICODE)

latitude_decimal_with_direction_regex = re.compile('^(-?[0-9][0-9](?:\.[0-9]+))[ ]*[ :°ºd]?[ ]*(N|n|S|s)$', re.I)
longitude_decimal_with_direction_regex = re.compile('^(-?1[0-8][0-9]|0?[0-9][0-9](?:\.[0-9]+))[ ]*[ :°ºd]?[ ]*(E|e|W|w)$', re.I)


def latlon_to_floats(latitude, longitude):
    have_lat = False
    have_lon = False

    latitude = safe_decode(latitude).strip(u' ,;|')
    longitude = safe_decode(longitude).strip(u' ,;|')

    latitude = latitude.replace(u',', u'.')
    longitude = longitude.replace(u',', u'.')

    lat_dms = latitude_dms_regex.match(latitude)
    lat_dir = latitude_decimal_with_direction_regex.match(latitude)

    if lat_dms:
        d, m, s, c = lat_dms.groups()
        sign = direction_sign(c)
        latitude = degrees_to_decimal(d or 0, m or 0, s or 0)
        have_lat = True
    elif lat_dir:
        d, c = lat_dir.groups()
        sign = direction_sign(c)
        latitude = float(d) * sign
        have_lat = True
    else:
        latitude = re.sub(beginning_re, u'', latitude)
        latitude = re.sub(end_re, u'', latitude)

    lon_dms = longitude_dms_regex.match(longitude)
    lon_dir = longitude_decimal_with_direction_regex.match(longitude)

    if lon_dms:
        d, m, s, c = lon_dms.groups()
        sign = direction_sign(c)
        longitude = degrees_to_decimal(d or 0, m or 0, s or 0)
        have_lon = True
    elif lon_dir:
        d, c = lon_dir.groups()
        sign = direction_sign(c)
        longitude = float(d) * sign
        have_lon = True
    else:
        longitude = re.sub(beginning_re, u'', longitude)
        longitude = re.sub(end_re, u'', longitude)

    return float(latitude), float(longitude)


def validate_latlon(props):
    try:
        latitude, longitude = latlon_to_floats(props['latitude'], props['longitude'])
        assert not (latitude == 0.0 and longitude == 0.0)
        props['latitude'] = latitude
        props['longitude'] = longitude
        return True
    except Exception as e:
        _ = props.pop('latitude', None)
        _ = props.pop('longitude', None)
        return False


def normalize_schema_dot_org_value(prop):
    value = prop.get('value', '').strip()
    value_attr = prop.get('value_attr')
    content_value = (prop.get('attributes') or {}).get('content', '')
    if content_value and not value_attr and len(content_value) > len(value):
        value = content_value
    return value


def schema_dot_org_props(item, item_type):
    have_address = False
    have_latlon = False
    have_name = False
    props = {}
    for prop in item.get('properties', []):
        name = prop.get('name', '').strip().lower()

        if name == 'address' or prop.get('type', '').lower() == 'postaladdress':
            address_props = prop.get('properties', [])
            for aprop in address_props:
                name = aprop.get('name', '').strip().lower()
                name = field_map.get(name, name)
                value = normalize_schema_dot_org_value(aprop)
                if name in street_props:
                    have_address = True
                if name and value:
                    props[name] = value
        elif name == 'geo':
            geo_props = prop.get('properties', [])
            for gprop in geo_props:
                name = gprop.get('name', '').strip().lower()
                name = field_map.get(name, name)
                value = normalize_schema_dot_org_value(gprop)
                if name in latlon_props:
                    have_latlon = True
                if name and value:
                    props[name] = value
        elif name == 'interactioncount':
            name = 'interaction_count'
            # Don't normalize here, longer content heuristic may not work for counts
            value = prop.get('value')
            if not value:
                continue
            props.setdefault(name, []).append(value)
        elif name == 'aggregaterating':
            name = 'aggregate_rating'
            for rprop in prop.get('properties', []):
                name = rprop.get('name', '').strip().lower()
                name = field_map.get(name, name)
                if name == 'rating_value' and rprop.get('value_attr') == 'src':
                    attrs = rprop.get('attributes', {})
                    value = attrs.get('content', attrs.get('alt', attrs.get('value', ''))).strip()
                else:
                    value = normalize_schema_dot_org_value(rprop)
                if name and value:
                    props[name] = value
        elif name == 'name':
            have_name = True
            value = prop.get('value')
            if prop.get('value_attr') == 'href':
                value = prop.get('text', '').strip()
                if not value:
                    have_name = False
                    continue
            props[name] = value
        elif name in SCHEMA_DOT_ORG_IGNORE_FIELDS:
            continue
        elif 'properties' not in prop:
            name = field_map.get(name, name)
            value = normalize_schema_dot_org_value(prop)                
            if name == 'street_address':
                have_address = True
            elif name in ('latitude', 'longitude'):
                have_latlon = True

            if name and value:
                props[name] = value

    if item.get('type'):
        if item['type'].lower() in UNINTERESTING_PLACE_TYPES:
            return None
        props['type'] = item['type']
    if have_latlon:
        have_latlon = validate_latlon(props)

    if props and have_name and have_latlon and have_address:
        props['item_type'] = item_type
        return props

    return None


def vcard_props(item):
    have_address = False
    have_latlon = False
    have_name = False
    props = {}
    prop_names = set([p.get('name', '').lower() for p in item.get('properties', [])])
    for prop in item.get('properties', []):
        name = prop.get('name', '').lower()
        value = prop.get('value', '').strip()
        if name in street_props and value:
            have_address = True
        elif name == 'org_name' or (name == 'name' and 'org_name' not in prop_names):
            have_name = True
            if prop.get('value_attr') == 'href':
                value = prop.get('text')
                if not value:
                    have_name = False
                    continue
        elif name == 'name' and 'org_name' in item:
            continue
        elif name in latitude_props:
            name = 'latitude'
            have_latlon = True
        elif name in longitude_props:
            name = 'longitude'
            have_latlon = True
        if name and value:
            props[name] = value

    if have_latlon:
        have_latlon = validate_latlon(props)

    if props and have_name and have_latlon and have_address:
        props['item_type'] = VCARD_TYPE
        return props


def og_props(item, item_type):
    have_address = False
    have_latlon = False
    have_name = False
    props = {}

    for key, value in item.iteritems():
        name = key.rsplit(':', 1)[-1].lower()

        if name in latitude_props:
            name = 'latitude'
            have_latlon = True
        elif name in longitude_props:
            name = 'longitude'
            have_latlon = True
        elif name in street_props:
            name = 'street_address'
            have_address = True
        elif name == 'title':
            name = 'name'
            have_name = True
        else:
            name = name.replace('-', '_')
        props[name] = value

    if have_latlon:
        have_latlon = validate_latlon(props)

    if props and have_name and have_latlon and (have_address or item_type == OG_BUSINESS_TAG_TYPE):
        props['item_type'] = item_type
        return props


def venue_to_geojson(props):
    latitude = props.pop('latitude', None)
    longitude = props.pop('longitude', None)
    if not latitude and longitude:
        return None
    return {'geometry': {'type': 'Point', 'coordinates': [longitude, latitude]},
            'type': 'Feature',
            'properties': props}
