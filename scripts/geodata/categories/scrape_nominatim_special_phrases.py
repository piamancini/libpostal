'''
scrape_nominatim_special_phrases.py
-----------------------------------

Simple script to scrape https://wiki.openstreetmap.org/wiki/Nominatim/Special_Phrases
for category-related phrases sometimes found in geocoder input.

Populates a per-language CSV with (phrase, OSM key, OSM value, plural):

OSM keys/values are like:

amenity=restaurant
tourism=museum
shop=books

Using these phrases, it is possible to construct queries like "restaurants in Brooklyn"
'''

import os
import re
import requests
import six
import sys
import time
import yaml

this_dir = os.path.realpath(os.path.dirname(__file__))
sys.path.append(os.path.realpath(os.path.join(os.pardir, os.pardir)))

from geodata.encoding import safe_decode, safe_encode

DEFAULT_CATEGORIES_DIR = os.path.join(this_dir, os.pardir, os.pardir, os.pardir,
                                      'resources', 'categories')


# Use Special:Export to get wiki markup
WIKI_BASE_URL = 'https://wiki.openstreetmap.org/wiki/Special:Export/'
NOMINATIM_SPECIAL_PHRASES_PREFIX = 'Nominatim/Special Phrases'
NOMINATIM_SPECIAL_PHRASES_URL = WIKI_BASE_URL + NOMINATIM_SPECIAL_PHRASES_PREFIX.replace(' ', '_')

phrase_table_re = re.compile('\| ([^|]+) \|\| ([^|]+) \|\| ([^|]+) \|\| ([^|]+) \|\| ([\-YN])', re.I)
wiki_link_re = re.compile('(?:\[\[([^\|\]]+(?<=\S))[\s]*(?:\|[\s]*)?(?:([^\]]+))?\]\])')

IGNORE_LANGUAGES = {
    # Interlingua
    'ia'
}


IGNORE_PLURAL_LANGUAGES = {
    # For Japanese, seems to just put an s on the end, which doesn't seem right
    # Need input from a native speaker on that one
    'ja',
}

# Wait this many seconds between page fetches
POLITENESS_DELAY = 5.0


def scrape_nominatim_category_page(url, ignore_plurals=False):
    result = requests.get(url)

    if not result or not result.content:
        return

    for phrase, key, value, operator, plural in phrase_table_re.findall(result.content):
        if operator and operator != '-':
            continue

        is_plural = plural == 'Y'
        if is_plural and ignore_plurals:
            continue

        yield safe_decode(phrase).lower(), key, value, is_plural


def scrape_all_nominatim_category_pages(url=NOMINATIM_SPECIAL_PHRASES_URL):
    print('Fetching main page')
    result = requests.get(url)
    languages = {}
    if not result or not result.content:
        return languages

    time.sleep(POLITENESS_DELAY)

    for entity, anchor_text in wiki_link_re.findall(result.content):
        if not entity.startswith(NOMINATIM_SPECIAL_PHRASES_PREFIX):
            continue

        lang = entity.rstrip('/').rsplit('/')[-1].lower()
        if lang in IGNORE_LANGUAGES:
            continue

        link = WIKI_BASE_URL + entity.replace(' ', '_')

        ignore_plurals = lang in IGNORE_PLURAL_LANGUAGES

        print('Doing {}'.format(lang))
        phrases = list(scrape_nominatim_category_page(link, ignore_plurals=ignore_plurals))
        time.sleep(POLITENESS_DELAY)

        if not phrases:
            continue

        languages[lang] = phrases

    return languages


def main(url=NOMINATIM_SPECIAL_PHRASES_URL, output_dir=DEFAULT_CATEGORIES_DIR):
    languages = scrape_all_nominatim_category_pages(url=url)
    for lang, phrases in six.iteritems(languages):
        filename = os.path.join(output_dir, '{}.yaml'.format(lang.lower()))
        with open(filename, 'w') as f:
            phrase_data = [
                {
                    # For sorting purposes, we'll remove later
                    '0phrase': safe_decode(phrase),
                    '1key': safe_decode(key),
                    '2value': safe_decode(value),
                    '3is_plural': is_plural
                }
                for phrase, key, value, is_plural in phrases
            ]

            yaml_data = yaml.safe_dump(phrase_data, allow_unicode=True, default_flow_style=False)

            yaml_data = yaml_data.replace('0phrase:', 'phrase:').replace('1key:', 'key:').replace('2value:', 'value:').replace('3is_plural:', 'is_plural:')

            f.write(yaml_data)

    print('Done')

if __name__ == '__main__':
    main()