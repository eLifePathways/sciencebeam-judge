import os

_RESOURCES_DIR = os.path.dirname(__file__)


def get_resource_path(filename: str) -> str:
    """Get the filesystem path to a bundled resource file."""
    return os.path.join(_RESOURCES_DIR, filename)


DEFAULT_XML_MAPPING_PATH = get_resource_path('xml-mapping.conf')
DEFAULT_EVALUATION_CONFIG_PATH = get_resource_path('evaluation.conf')
DEFAULT_EVALUATION_YAML_PATH = get_resource_path('evaluation.yml')
DEFAULT_EVALUATION_SCHEMA_PATH = get_resource_path('evaluation.schema.json')
