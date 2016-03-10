"""Python file for project 3 - Data Wrangling Final Project
In this project I will examine, clean, and load data from
OpenStreetMap into a MongoDB database. I will look for some
specific errors in the data, and correct them programatically.
I will also provide an overview of the data, and look at some
possible other applications of the data. I chose an area
around my home and work to investigate.

Author: Eric Carlsen
Date: 28 Feb 2016
"""

import re
from collections import defaultdict
from pprint import pprint
import xml.etree.cElementTree as ET


def is_street_name(elem):
    return elem.attrib['k'] == "addr:street"


def node_has_name(element):
    """
    Test if element has a name or not
    :param element: node level
    :return: True if has name, False if not
    """

    print_proj = False
    if element.attrib["id"] == "358948411":
        # print("Found element 566510041")
        print("Found element 358948411")
        print_proj = True

    # Return immediately and ignore if not a node
    if element.tag != "node" or element.find("tag") is None:
        return True

    if element.attrib["id"] == "566510041":
        print_proj = True
        print("Found element 566510041")

    # Look for node without name
    has_name = False
    has_amenity = False
    tags = element.findall("tag")
    if print_proj:
        print("Number of sub-elements in 'tag': {0}".format(len(tags)))
    # for tag in element.findall("tag"):
    #     this_key = tag.get("k")
    #     # print("tag.tag = {0}\ntag.k = {1}".format(tag.tag, tag.attrib['k']))
    #     if this_key == "name":
    #         has_name = True
    #     elif this_key == "amenity":
    #         has_amenity = True

    # If no name then print out ID
    if not has_name and has_amenity:
        print("No name for node id {0}".format(element.attrib['id']))

    return has_name


class AuditData(object):
    """This class is intended purely for auditing purposes of the
    openstreetmap data. It will not load or fix problems, but is
    useful in determining what problems exist. It may not be run
    in the final submitted version of the code, as it will
    mostly be used in finding issues that need to be fixed.
    """

    def __init__(self, filename):
        self.osmfile = filename
        self.street_type_re = re.compile(r'\b(\S+\.?)$', re.IGNORECASE)
        self.street_pre_re = re.compile(r'^([SENW]\.?)\s+', re.IGNORECASE)
        self.suite_re = re.compile(r'\b(ste\.?)\s\d+$', re.IGNORECASE)

        self.expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road",
                         "Trail", "Parkway", "Commons"]

    def audit_street_type(self, street_types, street_prefixes, street_suites, street_name):
        """
        :param street_types: Dictionary of street type by suffix (eg. Rd)
        :param street_prefixes: Dictionary of street type by prefix (eg. N)
        :param street_suites: Dictionary of street names that correspond to suites
        :param street_name: The name of the street
        :return: None
        """

        def find_match(regex, name, outdict, street_type=False):
            """
            Find the match for the regular expression and add to dictionary
            :param regex: Input regular expression
            :param name: String to search
            :param outdict: Output dictionary
            :param street_type: True for street type (St, Rd, etc.), false for other data types
            :return: None
            """
            re_results = regex.search(name)
            if re_results:
                re_result = re_results.groups()[0]
                if not street_type or re_result not in self.expected:
                    outdict[re_result].add(name)

        find_match(self.street_type_re, street_name, street_types, True)
        find_match(self.street_pre_re, street_name, street_prefixes, False)
        find_match(self.suite_re, street_name, street_suites, False)

    def audit(self):
        """
        Perform the auditing function
        """
        osm_file = open(self.osmfile, "r")
        street_types = defaultdict(set)
        street_prefixes = defaultdict(set)
        street_suites = defaultdict(set)
        for event, elem in ET.iterparse(osm_file, events=("start",)):
            if elem.tag == "node" or elem.tag == "way":
                node_has_name(elem)
                for tag in elem.iter("tag"):
                    if is_street_name(tag):
                        self.audit_street_type(street_types, street_prefixes, street_suites, tag.attrib['v'])
        osm_file.close()
        return street_types, street_prefixes, street_suites

    def test(self):
        """
        Test method
        :return: None
        """
        st_types, st_pres, st_ste = self.audit()
        print("Street Types:\n")
        pprint(dict(st_types))
        print("\nStreet Prefixes:\n")
        pprint(dict(st_pres))
        print("\nStreets with Abbreviated Suite:\n")
        pprint(dict(st_ste))


class CleanData(object):
    """This class performs the fixing of the data programatically before entering it into the baseline
    """
    pass


if __name__ == '__main__':
    audit_results = AuditData('centennial.osm')
    audit_results.test()
