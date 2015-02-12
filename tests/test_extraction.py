#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
import unittest

from openvenues.jobs.microdata import contains_microdata_regex
from openvenues.extract.soup import *
from openvenues.extract.util import *

this_dir = os.path.realpath(os.path.dirname(__file__))

TEST_DATA_DIR = os.path.join(this_dir, 'data')


class TestExtraction(unittest.TestCase):
    def _get_test_html(self, filename):
        return open(os.path.join(TEST_DATA_DIR, filename)).read()

    def test_filter_regex(self):
        for filename in os.listdir(TEST_DATA_DIR):
            html = self._get_test_html(filename)
            self.assertTrue(contains_microdata_regex.search(html))


    def test_schema_dot_org(self):
        html = self._get_test_html('opentable.html')
        soup = BeautifulSoup(br2nl(html))
        ret = extract_items(soup)

        have_schema_dot_org = False

        have_street = False
        have_locality = False
        have_region = False

        for item in ret.get('items', []):
            if item.get('item_type') == SCHEMA_DOT_ORG_TYPE:
                have_schema_dot_org = True

                for prop in item.get('properties', []):
                    name = prop.get('name')
                    value = prop.get('value')

                    if name == 'address':
                        for p in prop.get('properties', []):
                            aname = p.get('name')
                            avalue = p.get('value')
                            if aname == 'streetAddress':
                                have_street = True
                                self.assertEqual(avalue, '5425 NE 30th Ave\nPortland, OR  97211')
                                break

        self.assertTrue(have_schema_dot_org)
        self.assertTrue(have_street)

    def test_invalid_schema_dot_org(self):
        html = self._get_test_html('time.html')
        soup = BeautifulSoup(html)
        ret = extract_items(soup)
        self.assertEqual(ret, None)

    def test_rdfa(self):
        html = self._get_test_html('tripadvisor.html')
        soup = BeautifulSoup(html)
        ret = extract_items(soup)

        have_rdfa = False
        have_address = False

        have_latlon = False

        have_street = False
        have_locality = False
        have_region = False

        for item in ret.get('items', []):
            if item.get('item_type') == RDFA_TYPE:
                have_rdfa = True

                for prop in item.get('properties', []):
                    name = prop.get('name')
                    value = prop.get('value')

                    if name == 'street_address':
                        have_street = True
                        self.assertEqual(value, '781 Franklin Ave.')

                    if name == 'locality':
                        have_locality = True
                        self.assertEqual(value, 'Brooklyn')

                    if name == 'region':
                        have_region = True
                        self.assertEqual(value, 'NY')

            if item.get('item_type') == ADDRESS_ELEMENT_TYPE:
                have_address = True
                value = item.get('address')
                self.assertEqual(value, '781 Franklin Ave., Crown Heights, Brooklyn, NY')

            if item.get('item_type') == DATA_LATLON_TYPE:
                if item.get('latitude', '').strip() and item.get('longitude', '').strip():
                    have_latlon = True

        self.assertTrue(have_rdfa)
        self.assertTrue(have_latlon)
        self.assertTrue(have_street)
        self.assertTrue(have_locality)
        self.assertTrue(have_region)

        self.assertTrue(have_address)


    def test_vcard(self):
        html = self._get_test_html('timeout_london.html')
        soup = BeautifulSoup(html)
        ret = extract_items(soup)
        have_vcard = False

        have_name = False
        have_street = False
        have_locality = False
        have_postal_code = False
        have_latitude = False
        have_longitude = False
        have_telephone = False
        have_url = False

        for item in ret.get('items', []):
            if item.get('item_type') == VCARD_TYPE:
                have_vcard = True

                for prop in item.get('properties', []):
                    name = prop.get('name')
                    value = prop.get('value')

                    if name == 'name':
                        have_name = True
                        self.assertEqual(value, 'Hootananny')

                    if name == 'street_address':
                        have_street = True
                        self.assertEqual(value, '95 Effra Road')

                    if name == 'locality':
                        have_locality = True
                        self.assertEqual(value, 'London')

                    if name == 'postal_code':
                        have_postal_code = True
                        self.assertEqual(value, 'SW2 1DF')

                    if name == 'latitude':
                        have_latitude = True
                        self.assertEqual(value, '51.455668')

                    if name == 'longitude':
                        have_longitude = True
                        self.assertEqual(value, '-0.113469')

                    if name == 'telephone':
                        have_telephone = True
                        self.assertEqual(value, '020 7737 7273')

                    if name == 'url':
                        have_url = True
                        self.assertEqual(value, 'http://www.hootanannybrixton.co.uk')

        self.assertTrue(have_vcard)
        self.assertTrue(have_name)
        self.assertTrue(have_street)
        self.assertTrue(have_locality)
        self.assertTrue(have_postal_code)
        self.assertTrue(have_latitude)
        self.assertTrue(have_longitude)
        self.assertTrue(have_telephone)
        self.assertTrue(have_url)

    def test_vcard_non_standard(self):
        html = self._get_test_html('nymag.html')
        soup = BeautifulSoup(html)
        ret = extract_items(soup)
        have_vcard = False

        have_name = False
        have_street = False
        have_locality = False
        have_region = False
        have_postal_code = False
        have_latitude = False
        have_longitude = False
        have_category = False

        for item in ret.get('items', []):
            if item.get('item_type') == VCARD_TYPE:
                have_vcard = True

                for prop in item.get('properties', []):
                    name = prop.get('name')
                    value = prop.get('value')

                    if name == 'street_address':
                        have_street = True
                        self.assertEqual(value, '724 Franklin Ave.')

                    if name == 'locality':
                        have_locality = True
                        self.assertEqual(value, 'Brooklyn')

                    if name == 'region':
                        have_region = True
                        self.assertEqual(value, 'NY')

                    if name == 'postal_code':
                        have_postal_code = True
                        self.assertEqual(value, '11238')

                    if name == 'latitude':
                        have_latitude = True
                        self.assertEqual(value, '40.673822')

                    if name == 'longitude':
                        have_longitude = True
                        self.assertEqual(value, '-73.956851')

                    if name == 'category':
                        have_category = True
                        self.assertEqual(value, 'Cuisine: American Traditional')

        self.assertTrue(have_vcard)
        self.assertTrue(have_street)
        self.assertTrue(have_locality)
        self.assertTrue(have_region)
        self.assertTrue(have_postal_code)
        self.assertTrue(have_latitude)
        self.assertTrue(have_longitude)
        self.assertTrue(have_category)

    def test_vcard_title_class(self):
        html = self._get_test_html('visit_london.html')
        soup = BeautifulSoup(br2nl(html))
        ret = extract_items(soup)
        have_vcard = False

        have_name = False
        have_street = False
        have_locality = False
        have_postal_code = False
        have_latitude = False
        have_longitude = False
        have_telephone = False
        have_url = False

        for item in ret.get('items', []):
            if item.get('item_type') == VCARD_TYPE:
                have_vcard = True

                for prop in item.get('properties', []):
                    name = prop.get('name')
                    value = prop.get('value')

                    if name == 'name':
                        have_name = True
                        self.assertEqual(value, 'Hackney Empire Theatre')

                    if name == 'street_address':
                        have_street = True
                        self.assertEqual(value, '291 Mare Street\nHackney')

                    if name == 'region':
                        have_locality = True
                        self.assertEqual(value, 'London')

                    if name == 'postal_code':
                        have_postal_code = True
                        self.assertEqual(value, 'E8 1EJ')

                    if name == 'latitude':
                        have_latitude = True
                        self.assertEqual(value, '51.54611')

                    if name == 'longitude':
                        have_longitude = True
                        self.assertEqual(value, '-0.05541')

                    if name == 'telephone':
                        have_telephone = True
                        self.assertEqual(value, '+44 (0)20 8985 2424')

                break

        self.assertTrue(have_vcard)
        self.assertTrue(have_name)
        self.assertTrue(have_street)
        self.assertTrue(have_locality)
        self.assertTrue(have_postal_code)
        self.assertTrue(have_latitude)
        self.assertTrue(have_longitude)
        self.assertTrue(have_telephone)

if __name__ == '__main__':
    unittest.main()