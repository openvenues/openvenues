import os
import shutil
import string
import subprocess
import sys

import boto

import traceback
import warnings
import logging

from collections import *

from mrjob.protocol import *
from mrjob.job import *
import ujson as json

from mrjob.util import unarchive

from boto.s3.connection import Key, Bucket

import gzip
import warc

import re

from bs4 import UnicodeDammit, BeautifulSoup
import cgi
import cchardet

from requests.models import Response

from httplib import HTTPResponse
from cStringIO import StringIO
from gzipstream import GzipStreamFile

from collections import *
from itertools import chain, product

logger = logging.getLogger('commoncrawl_job')

logging.root.setLevel(logging.ERROR)

class JsonProtocol(PickleProtocol):
    def _loads(self, value):
        return json.loads(value)
    
    def _dumps(self, value):
        return json.dumps(value)

class BaseJob(MRJob):
    INTERNAL_PROTOCOL = JSONProtocol
    OUTPUT_PROTOCOL = JSONProtocol

class CommonCrawlJob(BaseJob):
    def jobconf(self):
        return {'mapreduce.input.fileinputformat.split.maxsize': '1'}


    def mapper(self, _, line):
        line = line.rstrip()

        filename = line.rsplit('/', 1)[-1]
        first_rec = None
        f = open(filename, 'w')
        #if self.options.runner in ('emr', 'hadoop'):
        for i in xrange(10):
            try:
                conn = boto.connect_s3(anon=True)
                bucket = conn.get_bucket('aws-publicdatasets')
                key = Key(bucket, line)
                key.get_contents_to_file(f)
                f = open(filename)
                records = warc.WARCFile(fileobj=GzipStreamFile(f))
                break
            except Exception as e:
                continue
        else:
            logger.error('10 attempts to get file {} failed, skipping...'.format(filename))
            return
 
        try:
            for i, record in enumerate(records):
                if record.type != 'response':
                    _ = record.payload.read()
                    continue
                for key, value in self.process_record(record):
                    yield key, value
                self.increment_counter('commoncrawl', 'processed_records', 1)
        except Exception:
            logger.error(traceback.format_exc())
        finally:
            f.close()
            os.unlink(filename)

class FakeSocket(object):
    def __init__(self, s):
        self.f = StringIO(s)

    def makefile(self, *args, **kw):
        return self.f
