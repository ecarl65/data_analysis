#!/usr/bin/env python
"""Python file for project 3 - Data Wrangling Final Project
In this project I will examine, clean, and load data from
OpenStreetMap into a MongoDB database. I will look for some
specific errors in the data, and correct them programatically.
I will also provide an overview of the data, and look at some
possible other applications of the data. I chose an area
around my home and work to investigate.

Author: Eric Carlsen
Date: 7 March 2016
"""

import re
from collections import defaultdict
from pprint import pprint
from lxml import etree
import codecs
import json
import subprocess as sp
from pymongo import MongoClient
from geopy.distance import vincenty


class AuditXML(object):
    """This class is intended purely for auditing purposes of the
    openstreetmap data. It will not load or fix problems, but is
    useful in determining what problems exist. It may not be run
    in the final submitted version of the code, as it will
    mostly be used in finding issues that need to be fixed.
    """

    def __init__(self, filename):
        """
        Pass in the filename to work on to initialize the object
        :param filename: Input filename
        :return: None
        """
        self.osmfile = filename
        self.street_type_re = re.compile(r'\b(\S+\.?)$', re.IGNORECASE)
        self.street_pre_re = re.compile(r'^([SENW]\.?)\s+', re.IGNORECASE)
        self.suite_re = re.compile(r'\b(ste\.?)\s\d+$', re.IGNORECASE)
        # self.keywords = re.compile(r'((?:amenity|name|building|housenumber)_\d*)')
        self.keywords = re.compile(r'(amenity|name|building|housenumber)_\d*')

        self.expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road",
                         "Trail", "Parkway", "Commons"]

    @staticmethod
    def is_street_name(elem):
        """
        Tests if element is a street address
        :param elem: Element
        :return: True if street address, False otherwise
        """

        return elem.attrib['k'] == "addr:street"

    @staticmethod
    def find_religion(element, no_religion):
        """
        Test if element has a name or not
        :param no_religion: List of node id's that are places of worship without religion
        :param element: node level
        :return: True if has name, False if not
        """

        # Look for node without name
        is_place_of_worship = False
        has_religion = False
        for tag in element.findall("tag"):
            k = tag.attrib["k"]
            v = tag.attrib["v"]
            if k == "amenity" and v == "place_of_worship":
                is_place_of_worship = True

            if k == "religion":
                has_religion = True

        if is_place_of_worship and not has_religion:
            print("No religion for place_of_worship {0} with id {1}".format(element.tag, element.attrib["id"]))
            no_religion.append(element.attrib["id"])

        return

    @staticmethod
    def find_fixme(elem, fixme):
        """
        Find the tags that have fixme as a key
        :param elem: Input element (node or way)
        :param fixme: List containing node ID's that have FIXMEs
        :return: None
        """
        for tag in elem.findall("tag"):
            if tag.attrib["k"].lower() == "fixme":
                print("FIXME in {0} with id {1}".format(elem.tag, elem.attrib["id"]))
                fixme.append(elem.attrib["id"])

        return

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

        if re.search(r'[.]', street_name):
            print("Before: {0}\nAfter: {1}".format(street_name, re.sub(r'[.]', '', street_name)))

    def audit(self):
        """
        Perform the auditing function
        :return: street_types dictionary, street prefixes dictionary, street suites dictionary
        """

        # Variables to populate
        street_types = defaultdict(set)
        street_prefixes = defaultdict(set)
        street_suites = defaultdict(set)
        fixme = []
        no_religion = []

        osm_file = open(self.osmfile, "r")
        for event, elem in etree.iterparse(osm_file, events=("start",)):
            if elem.tag == "node" or elem.tag == "way":

                # Find fix_me
                self.find_fixme(elem, fixme)

                # Find and audit street names
                for tag in elem.iter("tag"):
                    if self.is_street_name(tag):
                        self.audit_street_type(street_types, street_prefixes, street_suites, tag.attrib["v"])

                # Find places of worship without religion
                self.find_religion(elem, no_religion)

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


class CleanXML(object):
    """This class performs the fixing of the data programatically before entering it into the MongoDB database
    """

    def __init__(self, filename):
        """
        Initialize the object
        :param filename: The input .osm filename to process
        :return: None
        """

        self.filename = filename

        # Regular expressions
        self.lower = re.compile(r'^([a-z]|_)*$')
        self.lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
        self.problem_characters = re.compile(r'[=\+/&<>;\'"\?%#$@,\. \t\r\n]')
        self.street_types_re = (
            (re.compile(r'\bCt\b', re.I), 'Court'),
            (re.compile(r'\b(?:[rR]d|Raod)\b', re.I), 'Road'),
            (re.compile(r'\b(?:Strret|Streer|St)\b', re.I), 'Street'),
            (re.compile(r'\bPl\b', re.I), 'Place'),
            (re.compile(r'\bPkwy\b', re.I), 'Parkway'),
            (re.compile(r'\bLn\b', re.I), 'Lane'),
            (re.compile(r'\bDr\b', re.I), 'Drive'),
            (re.compile(r'\bCir\b', re.I), 'Circle'),
            (re.compile(r'\bBlvd\b', re.I), 'Boulevard'),
            (re.compile(r'\bAve\b', re.I), 'Avenue'),
        )
        self.street_prefixes_re = (
            (re.compile(r'\bS\b', re.I), 'South'),
            (re.compile(r'\bE\b', re.I), 'East'),
            (re.compile(r'\bN\b', re.I), 'North'),
            (re.compile(r'\bW\b', re.I), 'West'),
        )

        # Other variables
        self.created = ["version", "changeset", "timestamp", "user", "uid"]
        self.num_streets_corrected = defaultdict(int)
        self.num_streets_total = defaultdict(int)

    @staticmethod
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

    def fix_created(self, element):
        """
        Fix the keys that should be in created sub-dict
        :param element: Input xml element that is a node or way
        :return: dictionary with created sub-elements
        """
        created = {}
        for created_key in self.created:
            if created_key in element.attrib:
                val = element.attrib[created_key]
                # TODO Parse timestamp as python datetime object
                created[created_key] = val

        return created

    def fix_street(self, street):
        """
        Take in a string representing a street and fix the abbreviated prefix
        and street type
        :param street: String representing street (no housenumber)
        :return: Fixed string
        """

        # First remove all periods (audit step showed all periods don't belong)
        street = re.sub(r'[.]', '', street)

        # Fix prefixes
        for prefix_re, prefix_full in self.street_prefixes_re:
            street, n = prefix_re.subn(prefix_full, street)
            if n:
                break

        # Then fix the street types
        for type_re, type_full in self.street_types_re:
            street, n = type_re.subn(type_full, street)
            if n:
                break

        return street

    def shape_element(self, element):
        """
        Create the XML element ready for MongoDB import
        :param element: The current not or way element to parse
        :return: The dictionary of the node or way
        """

        node = defaultdict(dict)

        if element.tag == "bounds":
            node["type"] = "bounds"
            node["minlat"] = float(element.attrib["minlat"])
            node["minlon"] = float(element.attrib["minlon"])
            node["maxlat"] = float(element.attrib["maxlat"])
            node["maxlon"] = float(element.attrib["maxlon"])

            return dict(node)

        elif element.tag == "node" or element.tag == "way":

            # Created sub-element
            created = self.fix_created(element)
            if created:
                node['created'] = created

            # Lat and long
            lat_lon = self.get_lat_lon(element)
            if lat_lon:
                node['pos'] = lat_lon

            # Type
            if element.tag == "node":
                node['type'] = "node"
            else:
                node['type'] = "way"

            # ID
            node['id'] = element.attrib["id"]

            # Visible
            node["visible"] = element.get("visible")

            # Iterate through sub-values
            for tag in element.iter("tag"):

                # Get key/value pair
                k = tag.attrib['k']
                v = tag.attrib['v']

                # Ignore keys with problem characters
                if re.search(self.problem_characters, k):
                    continue

                # Parse address and other with sub-elements
                keys = k.split(':')
                if len(keys) == 1:
                    # If only one key just fill in place, all keys lower case
                    # except NHS (National Highway System) and "FIX_ME" (underscore for editor only)
                    if k.upper() == "FIXME" or k.upper() == "NHS":
                        node[k.upper()] = v
                    else:
                        node[k.lower()] = v
                else:
                    # If more than one then process according to extra rules

                    if len(keys) == 2 and keys[0] == "addr":
                        # Processing address
                        if keys[1] == "street":
                            # If street then fix street name and assign
                            self.num_streets_total[v] += 1
                            corrected = self.fix_street(v)
                            if corrected != v:
                                self.num_streets_corrected[v] += 1
                                # print("original: {0}, corrected: {1}".format(v, corrected))
                                v = corrected
                        node["address"][keys[1]] = v

                    elif len(keys) > 2 and keys[0] == "addr" and keys[1] == "street":
                        # Ignore redundant sub-fields of address
                        continue

                    elif len(keys) > 1:
                        # On other fields just
                        merged_k = "_".join(keys)
                        node[merged_k] = v
                    else:
                        assert "Should not arrive here"

            # Add node refs
            if element.tag == "way":
                node_refs = []
                for nd in element.iter("nd"):
                    node_refs.append(nd.attrib["ref"])

                if node_refs:
                    node['node_refs'] = node_refs

            return dict(node)
        else:
            return None

    def print_stats(self):
        """
        Print the results of how many streets were corrected
        :return: None
        """
        print("Total number of streets processed: {0}".format(len(self.num_streets_total)))
        print("Number of streets corrected: {0}".format(len(self.num_streets_corrected)))
        print("Percent of streets corrected: {0:.1f}%".format(
            100.0 * float(len(self.num_streets_corrected)) / (float(len(self.num_streets_total)) + 1e-7)))

        return

    def process_map(self, pretty=False):
        # You do not need to change this file
        file_out = "{0}.json".format(self.filename)
        data = []
        with codecs.open(file_out, "w") as fo:
            for _, element in etree.iterparse(self.filename):
                el = self.shape_element(element)
                if el:
                    data.append(el)
                    if pretty:
                        fo.write(json.dumps(el, indent=2) + "\n")
                    else:
                        fo.write(json.dumps(el) + "\n")
        return data

    @staticmethod
    def insert_into_mongo(database, collection, filename):
        """
        Insert the results from the process map method into a mongodb instance
        :param database: Name of the database to insert into
        :param collection: Name of the collection to use
        :param filename: Name of input file
        :return:
        """
        sp.call("mongoimport -d {0} -c {1} --file {2}".format(
            database, collection, filename + ".osm.json"), shell=True)

        return

    def test(self):
        # NOTE: if you are running this code on your computer, with a larger dataset,
        # call the process_map procedure with pretty=False. The pretty=True option adds
        # additional spaces to the output, making it significantly larger.
        data = self.process_map(False)
        # pprint.pprint(data)


class FixAndAnalyzeDB(object):
    """
    This class performs the data analysis phase of the project. It looks
    through the data imported into the database
    """

    def __init__(self, database, collection):
        """
        Initialize the object
        :param database: The name of the database to connect to
        :param collection: The name of the collection to use
        :return:
        """

        client = MongoClient('localhost:27017')
        self.collection = client[database][collection]
        self.area_km = 0
        self.num_ways = 0

        return

    def fix_cities(self, cities_corrections):
        """
        This method will find and fix erroneous city names in the database
        :param cities_corrections: Map of erroneous city
        :return:
        """
        # First report on the cities to show which ones are wrong
        res = self.collection.aggregate([{"$match": {"address.city": {"$exists": True}}},
                                         {"$group": {"_id": "$address.city", "count": {"$sum": 1}}},
                                         {"$sort": {"count": -1}}])
        print("City counts")
        for doc in res:
            print("City: {0:20s}, Count: {1}".format(doc["_id"], doc["count"]))
        print("")

        # Now loop through all corrections that need to be done and perform each save
        num_updated_cities = 0
        for incorrect_city in cities_corrections:
            res = self.collection.find({"address.city": incorrect_city})
            for doc in res:
                doc["address"]["city"] = cities_corrections[incorrect_city]
                self.collection.save(doc)
                num_updated_cities += 1
        print("Number of city records fixed: {0}".format(num_updated_cities))
        print("")

        return

    def data_overview(self):
        """
        Report basic statistics of the data
        :return: None
        """

        # Number of documents
        num_docs = self.collection.find().count()
        print("Number of documents in the database: {0}".format(num_docs))

        # Number of nodes
        num_nodes = self.collection.find({"type": "node"}).count()
        print("Number of nodes in the database: {0}".format(num_nodes))

        # Number of ways
        self.num_ways = self.collection.find({"type": "way"}).count()
        print("Number of ways in the database: {0}".format(self.num_ways))

        # Number of edits by ecarl65 - my osm username
        num_ecarl65 = self.collection.find({"created.user": "ecarl65"}).count()
        print("Number of edits by ecarl65: {0} ({1:.1f}%)".format(
            num_ecarl65, float(num_ecarl65) / num_docs * 100.0))

        # Total number of distinct users
        users = self.collection.distinct("created.user")
        print("Number of unique users: {0}".format(len(users)))

        # Total number of documents with "FIX_ME" tag
        num_fixme = self.collection.find({"FIXME": {"$exists": True}}).count()
        print("Number of documents with FIXME: {0}".format(num_fixme))

        # Find number churches
        num_churches = self.collection.find({"amenity": "place_of_worship"}).count()
        num_churches_wo_religion = self.collection.find(
            {"amenity": "place_of_worship", "religion": {"$exists": 0}}).count()
        print("Number of churches: {0}".format(num_churches))
        print("Number of churches without religion: {0}".format(num_churches_wo_religion))
        print("")

    def additional_ideas(self):
        """
        Print out results of additional queries
        :return:
        """

        # Report postal codes
        res = self.collection.aggregate([
            {"$match": {"type": "node", "address.postcode": {"$exists": True}}},
            {"$group": {"_id": "$address.postcode", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
            {"$limit": 6}
        ])
        print("Postcodes on nodes")
        for doc in res:
            print("Postcode: {0:7s}, Count: {1}".format(doc["_id"], doc["count"]))
        print("")

        # self.measured_area()

        # Find the bounding box of the downloaded section
        bounding_doc = self.collection.find({"type": "bounds"})
        bounding_box = list(bounding_doc)[0]
        self.area_km, d_lat_km, d_lon_km = self.compute_area(bounding_box['maxlat'], bounding_box['maxlon'],
                                                             bounding_box['minlat'], bounding_box['minlon'])
        print("Reported Minimum Latitude: {0}".format(bounding_box["minlat"]))
        print("Reported Maximum Latitude: {0}".format(bounding_box["maxlat"]))
        print("Reported Minimum Longitude: {0}".format(bounding_box["minlon"]))
        print("Reported Maximum Longitude: {0}".format(bounding_box["maxlon"]))
        print("Reported Distance Across Constant Latitude: {0:.3f} (km)".format(d_lat_km))
        print("Reported Distance Across Constant Longitude: {0:.3f} (km)".format(d_lon_km))
        print("Reported Area: {0:.3f} (km^2)".format(self.area_km))
        print("")

        # Number of ways suitable for cycling
        res = self.collection.aggregate([
            {"$match": {"type": "way", "highway": {"$exists": True}}},
            {"$group": {"_id": "$highway", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 12}
        ])
        print("Highways")
        for doc in res:
            print("Highway: {0:20s}, Count: {1}".format(doc["_id"], doc["count"]))
        print("")

        # Bicycle tag
        res = self.collection.aggregate([
            {"$match": {"type": "way"}},
            {"$group": {"_id": "$bicycle", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            # {"$limit": 12}
        ])
        print("Bicycle tags on ways")
        for doc in res:
            print("Bicycle: {0:20s}, Count: {1}".format(doc["_id"], doc["count"]))
        print("")

        # Percentage of bicycle allowable roads
        print("Percentage of bicycle allowed ways:")
        res = self.collection.aggregate([
            {"$match": {"type": "way", "$or": [
                    {"highway": "cycleway"},
                    {"bicycle": {"$in": ["yes", "designated", "permissive", "allowed"]}}]}},
            {"$group": {"_id": None, "count": {"$sum": 1}}}
        ])
        num_bike_ways = 0
        for doc in res:
            num_bike_ways = doc["count"]
        print("Number of ways in which bicycling is allowed: {0}".format(num_bike_ways))
        print("Percent of ways in which bicycling is allowed: {0:.1f}%".format(
            100.0 * num_bike_ways / (self.num_ways + 1e-7)
        ))

        # Find the number of bike shops
        num_bike_shops = self.collection.find(
            {"$or": [{"shop": "bicycle"}, {"shop_1": "bicycle"}]}
        ).count()
        print("Number of bike shops: {0}".format(num_bike_shops))
        print("Number of bike shops per km^2: {0:g}".format(float(num_bike_shops) / self.area_km))

        return

    def measured_area(self):
        """
        Measures the area of the data by taking the min/max lat/lon and
        finding the distance along the mid-points of the rectangle. It turns
        out this was unsuccessful, due to the fact that the data downloaded
        anything that crossed, or started, in the area of interest, but some
        ways went MUCH further than that area of interest. Althought some
        ways went further, that doesn't mean that all the data in that expanded
        region was collected, so this would give misleading further statistics.
        :return:
        """
        def extract_lat_or_lon(lat_lon, sort_type=1):
            """
            Extract the latitude or longitude min or max
            :param lat_lon: 'lat' or 'lon'
            :param sort_type: 1 for minimum, -1 for maximum
            :return: Extracted value
            """

            # Get minimum and maximum for latitude and longitude
            element_pos = 0
            if lat_lon == "lat":
                element_pos = 0
            elif lat_lon == "lon":
                element_pos = 1
            else:
                print("Pass in either 'lat' or 'lon' for field")
                return

            query = [
                {"$match": {"pos": {"$exists": 1}}},
                {"$project": {"_id": 0, lat_lon: {"$arrayElemAt": ["$pos", element_pos]}}},
                {"$sort": {lat_lon: sort_type}},
                {"$limit": 1}
            ]

            out_doc = self.collection.aggregate(query)
            val = [doc[lat_lon] for doc in out_doc][0]

            return val

        # Compute the area based on the content
        min_lat = extract_lat_or_lon("lat", 1)
        max_lat = extract_lat_or_lon("lat", -1)
        min_lon = extract_lat_or_lon("lon", 1)
        max_lon = extract_lat_or_lon("lon", -1)
        area_km, dist_lat_km, dist_lon_km = self.compute_area(max_lat, max_lon, min_lat, min_lon)
        print("Minimum Measured Latitude: {0}".format(min_lat))
        print("Maximum Measured Latitude: {0}".format(max_lat))
        print("Minimum Measured Longitude: {0}".format(min_lon))
        print("Maximum Measured Longitude: {0}".format(max_lon))
        print("Measured Area across latitude: {0:.3f} (km)".format(dist_lat_km))
        print("Measured Area across longitude: {0:.3f} (km)".format(dist_lon_km))
        print("Measured Area: {0:.3f} (km^2)".format(area_km))

        return

    @staticmethod
    def compute_area(max_lat, max_lon, min_lat, min_lon):
        """
        Compute the approximate area given bounding values in lat/lon
        :param max_lat: maximum latitude
        :param max_lon: maximum longitude
        :param min_lat: minimum latitude
        :param min_lon: minimum longitude
        :return: area_km: area in square km
        :return: dist_lat_km: distance across in km
        :return: dist_lon_km: distance in longitude in km
        """
        mean_lat = (min_lat + max_lat) / 2.0
        mean_lon = (min_lon + max_lon) / 2.0
        dist_lat_km = vincenty((mean_lat, min_lon), (mean_lat, max_lon)).km
        dist_lon_km = vincenty((min_lat, mean_lon), (max_lat, mean_lon)).km
        area_km = dist_lat_km * dist_lon_km

        return area_km, dist_lat_km, dist_lon_km


if __name__ == "__main__":
    # Variables
    # input_basename = "centennial"
    # database_name = "osm"
    # collection_name = "centennial"

    # Test
    input_basename = "centennial_sample"
    database_name = "test"
    collection_name = "test"

    # Audit data
    audit_results = AuditXML(input_basename + ".osm")
    audit_results.test()

    # Format data for output
    clean_results = CleanXML(input_basename + ".osm")
    clean_results.test()
    clean_results.print_stats()
    clean_results.insert_into_mongo(database_name, collection_name, input_basename)

    # Analyze results
    analyze_results = FixAndAnalyzeDB(database_name, collection_name)
    analyze_results.fix_cities({"Centenn": "Centennial"})
    analyze_results.data_overview()
    analyze_results.additional_ideas()
