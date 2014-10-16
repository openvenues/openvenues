openvenues
==========

Open information extraction project for indexing and normalizing real-world venue/POI information from across the Web. Can be used standalone to extract venues from individual websites, or on a full-fledged copy of the entire Internet using the [Common Crawl](http://commoncrawl.org/).

## Project layout

* extract: the "easy way", extract structured (or at least semi-structured) address and geo data from HTML markup. Supports schema.org microdata, RDFa Lite, hcard, geotags, HTML5 `<address>` elements, OpenGraph and extracting url params from Google map embeds
* jobs: Amazon Elastic Mapreduce jobs for extracting places from the Common Crawl (224TB or 3.6+ billion urls available on S3 as of August 2014, new crawls published periodically).

## Notes

### BeautifulSoup vs. lxml
The first version of the Common Crawl extraction job was written using lxml, a fast C library based on libxml2, for parsing. However, running said parser over billions of badly-encoded webpages revealed some bugs in lxml/libxml2 related to reading from uninitialized memory at the C level (see https://bugs.launchpad.net/lxml/+bug/1240696), which eats up all the system's memory and crashes the box. The bug occurs non-deterministically, so is hard to track down, but will occur, on different documents, if the job is run for long enough. Until there's a fix lxml won't be usable for this project. BeautifulSoup is a forgiving pure-Python regex-based "parser" designed for working with "tag soup". It's up to 100x slower than lxml, so we currently use a high-recall (not necessarily high-precision) regex to filter out documents that definitely don't contain the keywords we're looking for before committing to a full parse. With this filter, the job still completes in a reasonable amount of time using 100 8-core machines.

## Coming up next:
* Address extraction (find postal addresses in text)
* Deduping and normalization of venue names, addresses and locations
