import re

'''
Blacklisted source domains from the web/Common Crawl
which misclassify their pages as venue types
'''

NON_PLACE_DOMAINS = re.compile('|'.join([
    # Crime reports
    'spotcrime.com',

    # Auctions
    'bonhams.com',

    # Real-estate listings
    'rent.com',
    'ziprealty.com',
    'mynewplace.com',
    'houseplans.com',

    # Many geocoded articles are not places
    # More precise extraction is best
    'wikipedia.org',

    # Geocoded news
    'topix.com',
    'topix.net',

    # Fictional locations
    'doctorwholocations.net',

    # Metadata are actually cities
    'booking.com',
]), re.I)


'''
Whitelisted source domains from the web/Common Crawl using
ambiguous or varying OpenGraph types
'''
OG_WHITELIST_DOMAINS = re.compile('|'.join([
    # Use og:type = article
    'timeout\.com',
    'timeout\.jp',
    'au\.timeout\.com',
    'timeout\.com\.br',
    'timeoutcroatia\.com',
    'timeout\.fr',
    'timeoutistanbul\.com',
    'timeout\.ru',
    'timeoutdubai\.com',
    'timeoutcn\.com',
    'timeoutsingapore\.com',
    'timeoutdoha\.com',
    'nz\.timeout\.com',
    'timeout\.sapo\.pt',
    'timeoutabudhabi\.com',
    'timeout\.co\.il',
    'timeout\.co\.il',
    'timeoutbeirut\.com',
    'timeoutcn\.com',
    'timeout\.es',
    'timeoutbahrain\.com',
    'timeoutbeijing\.com',
    'timeoutcyprus\.com',
    'timeoutshanghai\.com',
    'timeoutbarcelona\.es',
    'timeoutmexico\.mx',
    'timeout\.com\.hk',
    'timeoutsydney\.com\.au',
    'timeout\.cat',

    'travelandleisure\.',

    # Also uses article. Only lists street-address and lat/lon tags for venues
    'partyearth\.com',

    # Custom og:type tags, all places
    'salir\.com',
    'yp\.com',
    'yellowpages\.com',
]), re.I)
