from openvenues.jobs.common_crawl import *
from openvenues.extract.soup import *

contains_microdata_regex = re.compile('vcard|itemtype|typeof|maps\.google|(?:(?:google.[a-z]+(?:\.[a-z]{2,3}){0,1})|(?:goo.gl))/maps|address|og:latitude|og:postal_code|og:street_address', re.I | re.UNICODE)

logger = logging.getLogger('microdata_job')

class MicrodataJob(CommonCrawlJob):
    valid_charsets = set(['utf-8', 'iso-8859-1', 'latin-1', 'ascii'])

    def prefix_key(self, prefix, key):
        return u'|'.join([prefix, key])
 
    def encoding_from_headers(self, content_type):
        if not content_type:
            return None

        content_type, params = cgi.parse_header(content_type)

        if 'charset' in params:
            return params['charset'].strip("'\"")

        if 'text' in content_type:
            return 'ISO-8859-1'        

    def detect_encoding(self, content):
        return cchardet.detect(content)['encoding'] 

    def report_items(self, items):
        self.increment_counter('commoncrawl', 'sites with places', 1)
        for item in items:
            item_type = item.get('item_type')
            if not item_type:
                continue
            if 'properties' in item:
                props = item['properties']
            else:
                props = [k for k in item.keys() if k != 'item_type']
            for prop in props:
                self.increment_counter('commoncrawl', u':'.join([item_type, prop]), 1)

    def report_social(self, social):
        for k, vals in social.iteritems():
            self.increment_counter('commoncrawl', 'url type {}'.format(k), len(vals))

    def process_record(self, record):
        content = None
        try:
            payload = record.payload.read()
            s = FakeSocket(payload)
            response = HTTPResponse(s)
            response.begin()

            status_code = response.status
            if status_code != 200:
                return

            content_type = response.getheader('Content-Type', '')
            if 'text/html' not in content_type:
                return

            content = response.read(len(payload))
        except Exception:
            return

        if content is not None:
            content = content.strip()

        if not content:
            return

        html = None

        try:
            encoding = self.encoding_from_headers(content_type)
            if encoding and encoding.lower() not in self.valid_charsets:
                return

            doc = UnicodeDammit(content, is_html=True)
            if not doc.unicode_markup or (doc.original_encoding and doc.original_encoding.lower() not in self.valid_charsets) or not contains_microdata_regex.search(doc.unicode_markup):
                return

            doc = doc.unicode_markup

            soup = BeautifulSoup(doc)

            have_item_scope = False

            items = []

            schema_dot_org_items = extract_schema_dot_org(soup)
            rdfa_items = extract_schema_dot_org(soup, use_rdfa=True)
            vcards = extract_vcards(soup)
            address_elements = extract_address_elements(soup)
            opengraph_tags = extract_opengraph_tags(soup)
            google_maps_embeds = extract_google_map_embeds(soup)
            geotags = extract_geotags(soup)

            if geotags:
                geotags = [geotags]

            basic_metadata = extract_basic_metadata(soup)



            items = list(chain(*(c for c in (schema_dot_org_items, rdfa_items, vcards, address_elements, geotags, google_maps_embeds) if c)))
            if opengraph_tags:
                i = opengraph_item(opengraph_tags)
                if i:
                    items.append(i)

            social_handles = extract_social_handles(soup)

            ret = {}
            if items:
                self.report_items(items)
                ret['items'] = items

                if social_handles:
                    ret['social'] = social_handles
                    self.report_social(social_handles)

                if opengraph_tags:
                    ret['og'] = opengraph_tags

                if basic_metadata:
                    ret.update(basic_metadata)

                yield record.url, ret
                items = []

        except Exception as e:
            logger.error(traceback.format_exc())
        finally:
            if html is not None:
                html.clear()
            return

if __name__ == '__main__':
   MicrodataJob.run() 