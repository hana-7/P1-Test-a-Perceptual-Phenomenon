
import xml.etree.cElementTree as ET
from collections import defaultdict
import re
import pprint

OSMFILE = 'san-jose_example.osm'
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)


expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road", 
            "Trail", "Parkway", "Commons",'Highway']

mapping = { "St": "Street",
            "St.": "Street",
           'st':'Street',
           'street':'Street',
           'Ave':'Avenue',
           'ave':'Avenue',
           'Blvd':'Boulevard',
           'Cir':'Circle',
           'Ln':'Lane',
           'Ct':'Court',
           'court':'Court',
           'Dr':'Drive',
           'Rd':'Road',
           'Hwy':'Highway',
           'Sq':'Square'
           
            }


def audit_street_type(street_types, street_name):
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected:
            street_types[street_type].add(street_name)


def is_street_name(elem):
    return (elem.attrib['k'] == "addr:street")


def audit(osmfile):
    osm_file = open(osmfile, "r")
    street_types = defaultdict(set)
    for event, elem in ET.iterparse(osm_file, events=("start",)):

        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_street_name(tag):
                    audit_street_type(street_types, tag.attrib['v'])
    osm_file.close()
    return street_types


def update_name(name, mapping):

    m = street_type_re.search(name)
    better_name = name
    # condition: if the street name does have a last word
    if m:
        # check if the street type is a key in your mapping dictionary:
        if m.group() in mapping.keys():
            better_street_type = mapping[m.group()]
            better_name = street_type_re.sub(better_street_type, name)
    return better_name

    return name


def test():
    st_types = audit(OSMFILE)
    pprint.pprint(dict(st_types))

    for st_type, ways in st_types.iteritems():
        for name in ways:
            better_name = update_name(name, mapping)
            print name, "=>", better_name

# update postal code to 5-digit format, drop leading stata abbreviation characters and 4-digit 
# postal code extension.

postcode_re = re.compile(r'[0-9]{5}')

def is_postcode(elem):
    return (elem.attrib['k'] == "addr:postcode")

def update_postcode(postcode):
    m = postcode_re.search(postcode)
    try:
        postcode = m.group()
    except:
        pass
    return postcode


import csv
import codecs
import re

import cerberus

import schema

OSM_PATH = "san-jose_california.osm"

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

SCHEMA = schema.schema

# Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']


def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    """Clean and shape node or way XML element to Python dict"""

    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handle secondary tags the same way for both node and way elements

    if element.tag == 'node':
        for key in element.attrib.keys():
            if key in NODE_FIELDS:
                node_attribs[key]=element.attrib[key]
        
        for child in element:
            node_tags={}
            if child.tag == 'tag':
                node_tags['id'] = element.attrib['id']
                node_tags['value']=child.attrib['v']
                problem=re.search(PROBLEMCHARS, child.get('k'))
                match = LOWER_COLON.search(child.attrib['k'])
                
                if problem:
                    continue
                
                elif match:
                    m = match.group()
                    tag_type = m.split(':')[0]
                    tag_key = m.split(':')[1]
                    node_tags['key'] = tag_key
                    node_tags['type'] = tag_type
                    
                    # Update street name and postal code
                    if is_street_name(child):
                        node_tags['value'] = update_name(child.attrib['v'], mapping)
                    elif is_postcode(child):
                        node_tags['value'] = update_postcode(child.attrib['v']) 
                                                        
                else:
                    node_tags['key']=child.attrib['k']
                    node_tags['type']='regular'
                
                if node_tags:    
                    tags.append(node_tags)
                    
        return {'node': node_attribs, 'node_tags': tags}
        
        
    elif element.tag == 'way':
        counter=0
        for key in element.attrib.keys():
            if key in WAY_FIELDS:
                way_attribs[key]=element.attrib[key]
        
        for child in element:
            way_tag={}
            way_node={}
            if child.tag == 'tag':
                way_tag['id'] = element.attrib['id']
                way_tag['value']=child.attrib['v']
                problem=re.search(PROBLEMCHARS, child.get('k'))
                match = LOWER_COLON.search(child.attrib['k'])
                
                if problem:
                    continue
                
                elif match:
                    m = match.group()
                    tag_key = child.attrib["k"].split(":", 1)[1]
                    tag_type = child.attrib["k"].split(":", 1)[0]
                    way_tag['key'] = tag_key
                    way_tag['type'] = tag_type
                    if is_street_name(child):
                        way_tag['value'] = update_name(child.attrib['v'], mapping) 
                    elif is_postcode(child):
                        way_tag['value'] = update_postcode(child.attrib['v']) 
                
                else:
                    way_tag['key']=child.attrib['k']
                    way_tag['type']='regular'
                    
                
                if way_tag:    
                    tags.append(way_tag)
    
                    
            elif child.tag == 'nd':
                
                way_node['id']=element.attrib['id']
                way_node['node_id']=child.attrib['ref']
                way_node['position']=counter
                counter+=1
                
                if way_node:
                    way_nodes.append(way_node)
            
        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)
        
        raise Exception(message_string.format(field, error_string))


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file, \
         codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
         codecs.open(WAYS_PATH, 'w') as ways_file, \
         codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
         codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])


if __name__ == '__main__':
    # Note: Validation is ~ 10X slower. For the project consider using a small
    # sample of the map when validating.
    process_map(OSM_PATH, validate=True)