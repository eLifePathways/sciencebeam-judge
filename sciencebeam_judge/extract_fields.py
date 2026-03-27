import argparse
import logging
import json
from io import BytesIO
from typing import List, Optional

from sciencebeam_utils.beam_utils.io import (
    read_all_from_path
)

from sciencebeam_judge.parsing.xml import parse_xml, parse_xml_mapping
from sciencebeam_judge.parsing.xpath.xpath_functions import register_functions

from sciencebeam_judge.evaluation_utils import comma_separated_str_to_list
from sciencebeam_judge.resources import DEFAULT_XML_MAPPING_PATH


LOGGER = logging.getLogger(__name__)


def parse_args(argv: List[str] = None):
    parser = argparse.ArgumentParser(
        description='Extract Fields from XML using XML Mapping',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    required_group = parser.add_argument_group('required')
    required_group.add_argument(
        '--xml-file', type=str, required=True,
        help='path to xml file to extract fields from'
    )
    required_group.add_argument(
        '--fields',
        type=comma_separated_str_to_list,
        default=None,
        help='comma separated list of fields to process'
    )
    config_group = parser.add_argument_group('config')
    config_group.add_argument(
        '--xml-mapping', type=str,
        default=DEFAULT_XML_MAPPING_PATH,
        help='filename to the xml mapping configuration'
    )
    return parser.parse_args(argv)


def run(
    xml_mapping_path: str,
    xml_file_path: str,
    field_names: Optional[List[str]] = None
):
    xml_mapping = parse_xml_mapping(xml_mapping_path)
    xml_content = read_all_from_path(xml_file_path)
    xml_data = parse_xml(
        BytesIO(xml_content),
        xml_mapping,
        fields=field_names,
        filename=xml_file_path
    )
    xml_data_json = json.dumps(xml_data, indent=2)
    print(xml_data_json)


def main(argv: List[str] = None):
    args = parse_args(argv=argv)
    LOGGER.info('main: args=%s', args)
    register_functions()
    run(
        xml_mapping_path=args.xml_mapping,
        xml_file_path=args.xml_file,
        field_names=args.fields
    )


if __name__ == '__main__':
    logging.basicConfig(level='INFO')
    main()
