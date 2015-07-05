#!/usr/bin/env python

import json
import os
import datetime
import email.utils
import email.mime.text
import urllib2
import textwrap
from BeautifulSoup import BeautifulSoup

def parse_pkg_html(ref):
    pg = BeautifulSoup(urllib2.urlopen('http://ascl.net/' + ref))
    item = pg.body.find('div', attrs={'class':'item'})
    ascl_id = item.find('span', attrs={'class':'ascl_id'})
    ascl_id = ascl_id.text
    if "submitted" in ascl_id:
        ascl_id = None
    title = item.find('span', attrs={'class':'title'}).text
    authors = item.find('div', attrs={'class':'credit'}).text
    abstract = item.find('div', attrs={'class':'abstract'}).text
    sites = item.find('dl', attrs={'class':'sites'})
    site = sites.find(text='Site:')
    if site is not None:
        site = [a['href']
                for a in site.parent.nextSibling.nextSibling('a')]
    else:
        site = []
    reference = sites.find(text='Ref:')
    if reference is not None:
        reference = [a['href']
                     for a in reference.parent.nextSibling.nextSibling('a')]
    else:
        reference = []
    bibcode = item.find('div', attrs={'class':'bibcode'})
    if bibcode is not None:
        bibcode = bibcode.text.split(':', 1)[1]
    fbref = item.find('fb:like')['href'].replace('http://ascl.net/', '')
    if ':' in title:
        name = title.split(':',1)[0]
        title = title.split(':',1)[1]
    else:
        name = None
    return {
        'ascl_id': ascl_id,
        'ascl_url': 'http://ascl.net/' + ref,
        'ascl_code_id': fbref,
        'name': name,
        'title': title,
        'authors': authors.split(';'),
        'abstract': abstract,
        'bibcode': bibcode,
        'site': site,
        'reference': reference,
        }

def parse_index_html(limit = 100):
    url = 'http://ascl.net/code/all/page/1/limit/{0}/order/date/listmode/compact/dir/desc'.format(limit)
    parsed_html = BeautifulSoup(urllib2.urlopen(url))
    return ((i.find('span', attrs={'class':'ascl_id'}).text,
             i.find('span', attrs={'class':'title'}).find('a')['href'][1:])
            for i in parsed_html.body('div', attrs={'class':'item'}))

def print_entry(pkg, accepted):
    print '%16s %s%s' % (pkg['ascl_id'],
                         pkg['name'] or pkg['title'],
                         (' (accepted from %s)' % pkg['ascl_code_id'])
                         if accepted else '')


def mail_entry(pkg, accepted):
    txt = textwrap.fill(pkg['abstract'], 72) + '\n\n'
    if len(pkg['site']) > 0:
           txt += 'Site: ' + '\n      '.join(pkg['site'])+'\n'
    if len(pkg['reference']) > 0:
           txt += 'Ref:  ' + '\n      '.join(pkg['reference'])+'\n'
    txt += 'Url:  ' + pkg['ascl_url']
    txt += '\n.\n'
    msg = email.mime.text.MIMEText(txt)
    if pkg['name'] is not None:
        subject = pkg['name']
    else:
        subject = pkg['ascl_id']
    if pkg['title'].strip() != pkg['name'].strip():
        subject += ': ' + pkg['title']
    if accepted:
        subject += ' (accepted from %s)' % pkg['ascl_code_id']
    msg['Subject'] = subject
    msg['From'] = '; '.join(pkg['authors'])
    msg['Date'] = email.utils.formatdate()
    msg['Newsgroups'] = 'ascl.packages'
    p = os.popen('/usr/sbin/snstore', 'w')
    p.write(str(msg))
    p.close()

def update_database(db, limit = 100, newentryhandler = None):
    changed = 0
    skipped = 0
    for id, ref in parse_index_html(limit):
        if ref in db:
            skipped += 1
            continue
        pkg = parse_pkg_html(ref)
        accepted = pkg['ascl_code_id'] in db
        if accepted:
            del db[pkg['ascl_code_id']]
        db[ref] = pkg
        changed += 1
        if newentryhandler:
            newentryhandler(pkg, accepted)
    return changed

def update_json(fname):
    try:
        with open(fname) as fp:
            pkgs = json.load(fp)
        changed = update_database(pkgs, 100, mail_entry)
    except IOError:
        pkgs = dict()
        changed = update_database(pkgs, -1, print_entry)
    if changed:
        with open('%s' % fname, 'w') as fp:
            json.dump(pkgs, fp, indent=4, sort_keys = True)
            fp.flush()
#        os.rename('%s.new' % fname, fname)

update_json('/home/ole/public_html/ascl.json')
