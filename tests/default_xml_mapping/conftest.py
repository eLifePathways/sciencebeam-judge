import pytest

from sciencebeam_judge.parsing.xml import parse_xml_mapping
from sciencebeam_judge.parsing.xpath.xpath_functions import register_functions
from sciencebeam_judge.resources import DEFAULT_XML_MAPPING_PATH


@pytest.fixture(scope='session')
def default_xml_mapping():
    register_functions()
    return parse_xml_mapping(DEFAULT_XML_MAPPING_PATH)
