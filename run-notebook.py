#!/usr/bin/python

import json, os, re, sys, urllib2

def exec_ipynb(filename_or_url):
    nb = (urllib2.urlopen(filename_or_url) if re.match(r'https?:', filename_or_url) else open(filename_or_url)).read()
    exec '\n'.join([''.join(cell['input']) for cell in json.loads(nb)['worksheets'][0]['cells'] if cell['cell_type'] == 'code']) in globals()

exec_ipynb(sys.argv[1])


