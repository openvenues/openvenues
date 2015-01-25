from common_crawl.base import *
from openvenues.extract.soup import *

logger = logging.getLogger('microdata_job')

patterns = [
    'vcard',
    'itemtype',
    'typeof',
    'maps\.google',
    'google\.[^/]+\/maps',
    '(?:goo\.gl)/maps',
    'address',
    'og:latitude',
    'og:postal_code',
    'og:street_address',
    'business:contact_data:street_address',
    'business:contact_data:postal_code',
    'place:location:latitude',
]

contains_microdata_regex = re.compile('|'.join(patterns), re.I | re.UNICODE)


class MicrodataJob(CommonCrawlJob):
    valid_charsets = set(['utf-8', 'iso-8859-1', 'latin-1', 'ascii'])

    def report_vcard_item(self, item):
        have_latlon = False
        for prop in item.get('properties'):
            propname = prop.get('name')
            if propname == 'street_address':
                self.increment_counter('commoncrawl', 'vcard:street_address')
            elif propname == 'postal_code':
                self.increment_counter('commoncrawl', 'vcard:postal_code')
            elif propname == 'org_name':
                self.increment_counter('commoncrawl', 'vcard:org_name')
            elif propname in ('latitude', 'longitude') and not have_latlon:
                self.increment_counter('commoncrawl', 'vcard:geo')
                have_latlon = True

    def report_schema_dot_org_item(self, item):
        have_address = False
        have_latlon = False
        for prop in item.get('properties'):
            if prop.get('name') == 'address' or prop.get('type') == 'PostalAddress':
                address_props = prop.get('properties', [])
                for aprop in address_props:
                    if aprop.get('name') == 'streetAddress':
                        have_address = True
            elif prop.get('name') == 'geo':
                geo_props = prop.get('properties', [])
                for gprop in geo_props:
                    if gprop.get('name') == 'latitude':
                        have_latlon = True
            elif prop.get('name') == 'latitude':
                have_latlon = True
            if have_address and have_latlon:
                break
        if have_address:
            self.increment_counter('commoncrawl', 'schema.org:address', 1)
        if have_latlon:
            self.increment_counter('commoncrawl', 'schema.org:geo', 1)

    def report_items(self, items):
        self.increment_counter('commoncrawl', 'sites with places', 1)
        for item in items:
            item_type = item.get('item_type')
            if not item_type:
                continue
            elif item_type == VCARD_TYPE:
                self.report_vcard_item(item)
            elif item_type == SCHEMA_DOT_ORG_TYPE:
                self.report_schema_dot_org_item(item)
            else:
                props = [k for k in item.keys() if k not in ('attributes',
                                                             'item_type',
                                                             'value_attr',
                                                             'text')]
                for prop in props:
                    self.increment_counter('commoncrawl', u':'.join([item_type,
                                                                     prop]), 1)

    def report_social(self, social):
        for k, vals in social.iteritems():
            self.increment_counter('commoncrawl', 'url type {}'.format(k),
                                   len(vals))

    def parse_content(self, content):
        return BeautifulSoup(content, 'html.parser')

    def filter(self, url, headers, content):
        return contains_microdata_regex.search(content)

    def process_html(self, url, headers, content, soup):
        ret = extract_items(soup)
        if not ret:
            return
        items = ret.get('items')
        if items:
            self.report_items(items)

        social_handles = ret.get('social_handles')
        if social_handles:
            self.report_social(social_handles)

        yield url, ret


if __name__ == '__main__':
    MicrodataJob.run()





