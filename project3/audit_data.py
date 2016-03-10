"""
Your task in this exercise has two steps:

- audit the OSMFILE and change the variable 'mapping' to reflect the changes needed to fix
    the unexpected street types to the appropriate ones in the expected list.
    You have to add mappings only for the actual problems you find in this OSMFILE,
    not a generalized solution, since that may and will depend on the particular area you are auditing.
- write the update_name function, to actually fix the street name.
    The function takes a string with street name as an argument and should return the fixed name
    We have provided a simple test so that you see what exactly is expected
"""
import xml.etree.cElementTree as ET
from collections import defaultdict
import re
import pprint

OSMFILE = "example4.osm"
# OSMFILE = "centennial.osm"
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
street_pre_re = re.compile(r'^([SENW]\.?)\s+', re.IGNORECASE)


expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road",
            "Trail", "Parkway", "Commons"]

# UPDATE THIS VARIABLE
mapping = {"St": "Street",
           "St.": "Street",
           "Ave.": "Avenue",
           "Rd.": "Road",
           "Ave": "Avenue",
           "Rd": "Road",
           }


def audit_street_type(street_types, street_prefixes, street_name):

    # Audit suffix
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected:
            street_types[street_type].add(street_name)

    # Audit prefix
    mm = street_pre_re.search(street_name)
    if mm:
        street_pre = mm.groups()[0]
        street_prefixes[street_pre].add(street_name)


def is_street_name(elem):
    return elem.attrib['k'] == "addr:street"


def audit(osmfile):
    osm_file = open(osmfile, "r")
    street_types = defaultdict(set)
    street_prefixes = defaultdict(set)
    for event, elem in ET.iterparse(osm_file, events=("start",)):
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_street_name(tag):
                    audit_street_type(street_types, street_prefixes, tag.attrib['v'])
    osm_file.close()
    return (street_types, street_prefixes)


def update_name(name, mapping):

    # YOUR CODE HERE
    for abbr in mapping:
        if name.find(abbr) >= 0:
            name = name.replace(abbr, mapping[abbr])
            if name.find(mapping[abbr] + '.'):
                name = name.replace(mapping[abbr] + '.', mapping[abbr])
            break

    return name


def test():
    st_types, st_pres = audit(OSMFILE)
    assert len(st_types) == 3
    pprint.pprint(dict(st_types))
    pprint.pprint(dict(st_pres))


if __name__ == '__main__':
    test()
