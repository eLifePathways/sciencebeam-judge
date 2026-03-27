from typing import Dict, List, NamedTuple, Optional

import yaml

from sciencebeam_utils.utils.string import parse_list

from .utils.string import parse_dict
from .utils.config import parse_config_as_dict
from .resources import DEFAULT_EVALUATION_YAML_PATH


DEFAULT_EVALUATION_YAML_FILENAME = DEFAULT_EVALUATION_YAML_PATH


class CustomEvaluationFieldSourceConfig(NamedTuple):
    field_names: List[str]

    @staticmethod
    def from_json(data: dict):
        return CustomEvaluationFieldSourceConfig(
            field_names=data['field_names']
        )


class CustomEvaluationFieldConfig(NamedTuple):
    name: str
    evaluation_type: str
    expected: CustomEvaluationFieldSourceConfig
    actual: CustomEvaluationFieldSourceConfig
    evaluation_type_config: Optional[dict] = None

    @staticmethod
    def from_json(data: dict):
        return CustomEvaluationFieldConfig(
            name=data['name'],
            evaluation_type=data['evaluation_type'],
            expected=CustomEvaluationFieldSourceConfig.from_json(data['expected']),
            actual=CustomEvaluationFieldSourceConfig.from_json(data['actual']),
            evaluation_type_config=data.get('evaluation_type_config')
        )


class CustomEvaluationConfig(NamedTuple):
    fields: List[CustomEvaluationFieldConfig]

    @staticmethod
    def from_json(data: Optional[dict]):
        if not data:
            return None
        return CustomEvaluationConfig(
            fields=[
                CustomEvaluationFieldConfig.from_json(field_data)
                for field_data in data['fields']
            ]
        )


class EvaluationConfig(NamedTuple):
    custom: CustomEvaluationConfig = CustomEvaluationConfig(fields=[])

    @staticmethod
    def from_json(data: dict):
        return EvaluationConfig(
            custom=CustomEvaluationConfig.from_json(
                data.get('custom')
            )
        )


def parse_evaluation_config(filename_or_fp) -> Dict[str, Dict[str, str]]:
    return parse_config_as_dict(filename_or_fp)


def parse_evaluation_yaml_config(filename_or_fp) -> dict:
    if isinstance(filename_or_fp, str):
        with open(filename_or_fp, 'r') as fp:
            return yaml.safe_load(fp)
    return yaml.safe_load(filename_or_fp)


def get_evaluation_config_object(evaluation_json: dict) -> EvaluationConfig:
    return EvaluationConfig.from_json(evaluation_json)


def parse_scoring_type_overrides(
        scoring_type_overrides_str: str) -> Dict[str, List[str]]:
    return {
        key: parse_list(value)
        for key, value in parse_dict(scoring_type_overrides_str).items()
    }


def get_scoring_types_by_field_map_from_config(
        config_map: Dict[str, Dict[str, str]]) -> Dict[str, List[str]]:
    scoring_type_config = config_map.get('scoring_type', {})
    return {
        key: parse_list(value)
        for key, value in scoring_type_config.items()
    }
