import json
from pathlib import Path
from io import StringIO

import yaml
import jsonschema

from sciencebeam_judge.evaluation_config import (
    parse_evaluation_config,
    parse_evaluation_yaml_config,
    get_evaluation_config_object,
    get_scoring_types_by_field_map_from_config,
    DEFAULT_EVALUATION_YAML_FILENAME
)
from sciencebeam_judge.resources import DEFAULT_EVALUATION_SCHEMA_PATH


class TestParseEvaluationConfig:
    def test_should_parse_config(self):
        config_content = u'\n'.join([
            '[scoring_type]',
            'default = set',
            'title = string'
        ])
        result = parse_evaluation_config(StringIO(config_content))
        assert result == {
            'scoring_type': {
                'default': 'set',
                'title': 'string'
            }
        }


class TestParseEvaluationYamlConfig:
    def test_should_validate(self):
        config_json = yaml.safe_load(Path(DEFAULT_EVALUATION_YAML_FILENAME).read_text())
        json_schema = json.loads(Path(DEFAULT_EVALUATION_SCHEMA_PATH).read_text())
        jsonschema.validate(config_json, json_schema)

    def test_should_parse_default_config_from_stream(self):
        config = parse_evaluation_yaml_config(
            StringIO(Path(DEFAULT_EVALUATION_YAML_FILENAME).read_text())
        )
        assert config
        assert config.get('custom')

    def test_should_parse_default_config_from_filename(self):
        config = parse_evaluation_yaml_config(DEFAULT_EVALUATION_YAML_FILENAME)
        assert config
        assert config.get('custom')


class TestGetEvaluationConfigObject:
    def test_should_allow_empty_config(self):
        config = get_evaluation_config_object({})
        assert config.custom is None

    def test_should_parse_custom_config(self):
        config = get_evaluation_config_object({
            'custom': {
                'fields': [{
                    'name': 'field1',
                    'evaluation_type': 'evaluation_type1',
                    'evaluation_type_config': {
                        'some_param': 'value1'
                    },
                    'expected': {
                        'field_names': ['expected1']
                    },
                    'actual': {
                        'field_names': ['actual1']
                    }
                }]
            }
        })
        assert config.custom is not None
        fields = config.custom.fields
        assert fields[0].name == 'field1'
        assert fields[0].evaluation_type == 'evaluation_type1'
        assert fields[0].evaluation_type_config == {
            'some_param': 'value1'
        }
        assert fields[0].expected.field_names == ['expected1']
        assert fields[0].actual.field_names == ['actual1']


class TestGetScoringTypeByFieldMapFromConfig:
    def test_should_return_scoring_type_map(self):
        assert get_scoring_types_by_field_map_from_config({
            'scoring_type': {
                'default': 'set',
                'title': 'string'
            }
        }) == {
            'default': ['set'],
            'title': ['string']
        }

    def test_should_parse_comma_separated_scoring_types(self):
        assert get_scoring_types_by_field_map_from_config({
            'scoring_type': {
                'default': 'set',
                'title': 'list, set'
            }
        }) == {
            'default': ['set'],
            'title': ['list', 'set']
        }
