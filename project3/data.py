#!/usr/bin/env python
# -*- coding: utf-8 -*-
import xml.etree.cElementTree as ET
import pprint
import re
import codecs
import json
from collections import defaultdict

"""
Your task is to wrangle the data and transform the shape of the data
into the model we mentioned earlier. The output should be a list of dictionaries
that look like this:

{
"id": "2406124091",
"type: "node",
"visible":"true",
"created": {
          "version":"2",
          "changeset":"17206049",
          "timestamp":"2013-08-03T16:43:42Z",
          "user":"linuxUser16",
          "uid":"1219059"
        },
"pos": [41.9757030, -87.6921867],
"address": {
          "housenumber": "5157",
          "postcode": "60625",
          "street": "North Lincoln Ave"
        },
"amenity": "restaurant",
"cuisine": "mexican",
"name": "La Cabana De Don Luis",
"phone": "1 (773)-271-5176"
}

You have to complete the function 'shape_element'.
We have provided a function that will parse the map file, and call the function with the element
as an argument. You should return a dictionary, containing the shaped data for that element.
We have also provided a way to save the data in a file, so that you could use
mongoimport later on to import the shaped data into MongoDB.

Note that in this exercise we do not use the 'update street name' procedures
you worked on in the previous exercise. If you are using this code in your final
project, you are strongly encouraged to use the code from previous exercise to
update the street names before you save them to JSON.

In particular the following things should be done:
+ you should process only 2 types of top level tags: "node" and "way"
+ all attributes of "node" and "way" should be turned into regular key/value pairs, except:
    + attributes in the CREATED array should be added under a key "created"
    + attributes for latitude and longitude should be added to a "pos" array,
      for use in geospacial indexing. Make sure the values inside "pos" array are floats
      and not strings.
+ if the second level tag "k" value contains problematic characters, it should be ignored
+ if the second level tag "k" value starts with "addr:", it should be added to a dictionary "address"
+ if the second level tag "k" value does not start with "addr:", but contains ":", you can
  process it in a way that you feel is best. For example, you might split it into a two-level
  dictionary like with "addr:", or otherwise convert the ":" to create a valid key.
+ if there is a second ":" that separates the type/direction of a street,
  the tag should be ignored, for example:

<tag k="addr:housenumber" v="5158"/>
<tag k="addr:street" v="North Lincoln Avenue"/>
<tag k="addr:street:name" v="Lincoln"/>
<tag k="addr:street:prefix" v="North"/>
<tag k="addr:street:type" v="Avenue"/>
<tag k="amenity" v="pharmacy"/>

  should be turned into:

{...
"address": {
    "housenumber": 5158,
    "street": "North Lincoln Avenue"
}
"amenity": "pharmacy",
...
}

- for "way" specifically:

  <nd ref="305896090"/>
  <nd ref="1719825889"/>

should be turned into
"node_refs": ["305896090", "1719825889"]
"""


lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)


CREATED = ["version", "changeset", "timestamp", "user", "uid"]


def fix_created(element):
    """
    Fix the keys that should be in created sub-dict
    :param element: Input xml element that is a node or way
    :return: dictionary with created sub-elements
    """
    created = {}
    for created_key in CREATED:
        if element.get(created_key):
            val = element.get(created_key)
            created[created_key] = val

    return created


def get_lat_lon(element):
    """
    Get latitude and longitude, if present, and return in array
    :param element: XML element, node or way only
    :return: [lat, lon] both in float format, or [] for None
    """
    lat_lon = []
    lat = element.get('lat')
    lon = element.get('lon')
    if lat and lon:
        lat_lon = [float(lat), float(lon)]

    return lat_lon


def shape_element(element):
    # node = {}
    node = defaultdict(dict)
    street_types = defaultdict(set)
    if element.tag == "node" or element.tag == "way":

        # YOUR CODE HERE
        created = fix_created(element)
        if created:
            node['created'] = created

        # Lat and long
        lat_lon = get_lat_lon(element)
        if lat_lon:
            node['pos'] = lat_lon

        # Type
        if element.tag == "node":
            node['type'] = "node"
        else:
            node['type'] = "way"

        # ID
        node['id'] = element.get("id")

        # Visible
        node["visible"] = element.get("visible")

        # Iterate through sub-values
        for tag in element.iter("tag"):

            # Ignore keys with problem characters
            k = tag.get('k')
            v = tag.get('v')
            if re.search(problemchars, k):
                continue

            # Parse address and other with sub-elements
            keys = k.split(':')
            if len(keys) == 1:
                node[keys[0]] = v
            else:
                if len(keys) == 2 and keys[0] == "addr":
                    node["address"][keys[1]] = v
                elif len(keys) > 2 and keys[0] == "addr" and keys[1] == "street":
                    continue
                elif len(keys) > 1:
                    merged_k = "_".join(keys)
                    node[merged_k] = v
                else:
                    assert "Should not arrive here"

            # Audit street types
            # if is_street_name(tag):
            #     audit_street_type(street_types, tag.attrib['v'])

        # Add node refs
        if element.tag == "way":
            node_refs = []
            for nd in element.iter("nd"):
                node_refs.append(nd.get("ref"))

            if node_refs:
                node['node_refs'] = node_refs

        return dict(node)
    else:
        return None


def process_map(file_in, pretty=False):
    # You do not need to change this file
    file_out = "{0}.json".format(file_in)
    data = []
    with codecs.open(file_out, "w") as fo:
        for _, element in ET.iterparse(file_in):
            el = shape_element(element)
            if el:
                data.append(el)
                if pretty:
                    fo.write(json.dumps(el, indent=2)+"\n")
                else:
                    fo.write(json.dumps(el) + "\n")
    return data


def test():
    # NOTE: if you are running this code on your computer, with a larger dataset,
    # call the process_map procedure with pretty=False. The pretty=True option adds
    # additional spaces to the output, making it significantly larger.
    data = process_map('example5.osm', True)
    # data = process_map('denver-boulder_colorado.osm', False)
    # data = process_map('ecc_area.osm', False)
    # data = process_map('centennial.osm', False)
    # pprint.pprint(data)

    correct_first_elem = {
        "id": "261114295",
        "visible": "true",
        "type": "node",
        "pos": [41.9730791, -87.6866303],
        "created": {
            "changeset": "11129782",
            "user": "bbmiller",
            "version": "7",
            "uid": "451048",
            "timestamp": "2012-03-28T18:31:23Z"
        }
    }
    assert data[0] == correct_first_elem
    assert data[-1]["address"] == {
                                   "street": "West Lexington St.",
                                   "housenumber": "1412"
                                  }
    assert data[-1]["node_refs"] == ["2199822281", "2199822390",  "2199822392", "2199822369",
                                     "2199822370", "2199822284", "2199822281"]

if __name__ == "__main__":
    test()
