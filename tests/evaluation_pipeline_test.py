import logging
from pathlib import Path
from unittest.mock import patch, MagicMock, DEFAULT

import pytest

from sciencebeam_utils.beam_utils.testing import (
    BeamTest,
    TestPipeline
)

from sciencebeam_utils.utils.collection import (
    extend_dict
)

from sciencebeam_judge.evaluation_config import parse_scoring_type_overrides

import sciencebeam_judge.evaluation_pipeline as evaluation_pipeline
from sciencebeam_judge.evaluation_pipeline import (
    flatten_evaluation_results,
    flatten_summary_results,
    get_all_source_field_names,
    configure_pipeline,
    get_scoring_types_by_field_map,
    parse_args,
    DataProps,
    OutputColumns,
    SummaryOutputColumns
)

from sciencebeam_judge.evaluation.match_scoring import MatchScoringProps
from sciencebeam_judge.evaluation.scoring_methods.scoring_methods import ScoringMethodNames
from sciencebeam_judge.evaluation.scoring_types.scoring_types import ScoringTypeNames
from sciencebeam_judge.evaluation.document_scoring import DocumentScoringProps
from sciencebeam_judge.evaluation.score_aggregation import SummaryScoresProps
from sciencebeam_judge.evaluation_config import (
    CustomEvaluationFieldSourceConfig,
    CustomEvaluationFieldConfig,
    CustomEvaluationConfig,
    EvaluationConfig,
    get_scoring_types_by_field_map_from_config
)


LOGGER = logging.getLogger(__name__)

BASE_TEST_PATH = '.temp/test/evaluation-pipeline'

TARGET_FILE_LIST_PATH = 'target-file-list.csv'
PREDICTION_FILE_LIST_PATH = 'prediction-file-list.csv'

TARGET_FILE_LIST = ['file1.nxml', 'file2.nxml']
PREDICTION_FILE_LIST = ['file1.pred.xml', 'file2.pred.xml']

FILE_LIST_MAP = {
    TARGET_FILE_LIST_PATH: TARGET_FILE_LIST,
    PREDICTION_FILE_LIST_PATH: PREDICTION_FILE_LIST
}

SINGLE_FILE_LIST_MAP = {
    TARGET_FILE_LIST_PATH: TARGET_FILE_LIST[:1],
    PREDICTION_FILE_LIST_PATH: PREDICTION_FILE_LIST[:1]
}

OUTPUT_PATH = BASE_TEST_PATH + '/out'

MIN_ARGV = [
    '--target-file-list=' + TARGET_FILE_LIST_PATH,
    '--prediction-file-list=' + PREDICTION_FILE_LIST_PATH,
    '--output-path=' + OUTPUT_PATH
]

FIELD_1 = 'field1'
FIELD_2 = 'field2'

MATCH_SCORE_1 = {
    MatchScoringProps.EXPECTED_SOMETHING: True,
    MatchScoringProps.ACTUAL_SOMETHING: True,
    MatchScoringProps.SCORE: 1.0,
    MatchScoringProps.TRUE_POSITIVE: 1,
    MatchScoringProps.TRUE_NEGATIVE: 0,
    MatchScoringProps.FALSE_POSITIVE: 0,
    MatchScoringProps.FALSE_NEGATIVE: 0,
    MatchScoringProps.BINARY_EXPECTED: 1,
    MatchScoringProps.BINARY_ACTUAL: 1,
    MatchScoringProps.EXPECTED: 'expected',
    MatchScoringProps.ACTUAL: 'actual',
    MatchScoringProps.EXPECTED_CONTEXT: 'expected_context1',
    MatchScoringProps.ACTUAL_CONTEXT: 'actual_context1'
}


def setup_module():
    logging.basicConfig(level='DEBUG')


def get_default_args():
    return parse_args(MIN_ARGV)


def patch_conversion_pipeline(**kwargs):
    always_mock = {
        'parse_xml_mapping',
        'parse_evaluation_config',
        'load_file_list',
        'read_all_from_path',
        'evaluate_file_pairs'
    }

    return patch.multiple(
        evaluation_pipeline,
        **{
            k: kwargs.get(k, DEFAULT)
            for k in always_mock
        }
    )


@pytest.fixture(name='get_evaluation_config_mock')
def _get_evaluation_config_mock():
    with patch.object(evaluation_pipeline, 'get_evaluation_config') as mock:
        yield mock


def load_file_list_side_effect(file_list_map):
    return lambda key, **kwargs: file_list_map[key]


def dummy_file_content(filename):
    return b'dummy file content: %s' % filename.encode('utf-8')


def read_all_from_path_side_effect():
    return lambda filename, **kwargs: dummy_file_content(filename)


class TestFlattenEvaluationResults:
    def test_should_convert_empty_evaluation_results(self):
        evaluation_results = {
            DataProps.PREDICTION_FILE_URL: PREDICTION_FILE_LIST[0],
            DataProps.TARGET_FILE_URL: TARGET_FILE_LIST[0],
            DataProps.EVALUTATION_RESULTS: []
        }
        assert flatten_evaluation_results(
            evaluation_results, field_names=[FIELD_1]
        ) == []

    def test_should_convert_single_evaluation_results(self):
        evaluation_results = {
            DataProps.PREDICTION_FILE_URL: PREDICTION_FILE_LIST[0],
            DataProps.TARGET_FILE_URL: TARGET_FILE_LIST[0],
            DataProps.EVALUTATION_RESULTS: [{
                DocumentScoringProps.FIELD_NAME: FIELD_1,
                DocumentScoringProps.SCORING_METHOD: ScoringMethodNames.EXACT,
                DocumentScoringProps.SCORING_TYPE: ScoringTypeNames.STRING,
                DocumentScoringProps.MATCH_SCORE: MATCH_SCORE_1
            }]
        }
        assert flatten_evaluation_results(evaluation_results, field_names=[FIELD_1]) == [{
            OutputColumns.PREDICTION_FILE: PREDICTION_FILE_LIST[0],
            OutputColumns.TARGET_FILE: TARGET_FILE_LIST[0],
            OutputColumns.FIELD_NAME: FIELD_1,
            OutputColumns.EVALUATION_METHOD: ScoringMethodNames.EXACT,
            OutputColumns.SCORING_TYPE: ScoringTypeNames.STRING,
            OutputColumns.TP: MATCH_SCORE_1[MatchScoringProps.TRUE_POSITIVE],
            OutputColumns.FP: MATCH_SCORE_1[MatchScoringProps.FALSE_POSITIVE],
            OutputColumns.FN: MATCH_SCORE_1[MatchScoringProps.FALSE_NEGATIVE],
            OutputColumns.TN: MATCH_SCORE_1[MatchScoringProps.TRUE_NEGATIVE],
            OutputColumns.EXPECTED: MATCH_SCORE_1[MatchScoringProps.EXPECTED],
            OutputColumns.ACTUAL: MATCH_SCORE_1[MatchScoringProps.ACTUAL],
            OutputColumns.EXPECTED_CONTEXT: MATCH_SCORE_1.get(MatchScoringProps.EXPECTED_CONTEXT),
            OutputColumns.ACTUAL_CONTEXT: MATCH_SCORE_1.get(MatchScoringProps.ACTUAL_CONTEXT)
        }]

    def test_should_convert_sub_scores_as_individual_rows(self):
        evaluation_results = {
            DataProps.PREDICTION_FILE_URL: PREDICTION_FILE_LIST[0],
            DataProps.TARGET_FILE_URL: TARGET_FILE_LIST[0],
            DataProps.EVALUTATION_RESULTS: [{
                DocumentScoringProps.FIELD_NAME: FIELD_1,
                DocumentScoringProps.SCORING_METHOD: ScoringMethodNames.EXACT,
                DocumentScoringProps.SCORING_TYPE: ScoringTypeNames.STRING,
                DocumentScoringProps.MATCH_SCORE: extend_dict(MATCH_SCORE_1, {
                    MatchScoringProps.SUB_SCORES: [
                        MATCH_SCORE_1,
                        MATCH_SCORE_1
                    ]
                })
            }]
        }
        result = flatten_evaluation_results(
            evaluation_results, field_names=[FIELD_1]
        )
        assert len(result) == 2
        assert result[0][OutputColumns.EXPECTED] == MATCH_SCORE_1[MatchScoringProps.EXPECTED]
        assert result[1][OutputColumns.EXPECTED] == MATCH_SCORE_1[MatchScoringProps.EXPECTED]


class TestFlattenSummaryResults:
    def test_should_convert_empty_evaluation_results(self):
        summary_results = []
        assert flatten_summary_results(
            summary_results, field_names=[FIELD_1]
        ) == []

    def test_should_convert_single_evaluation_results(self):
        scores = {
            'accuracy': 1.0,
            'f1': 1.0,
            'jaccard': 1.0,
            'precision': 1.0,
            'recall': 1.0
        }
        field_totals = MATCH_SCORE_1
        summary_results = [{
            DataProps.PREDICTION_FILE_URL: PREDICTION_FILE_LIST[0],
            DataProps.TARGET_FILE_URL: TARGET_FILE_LIST[0],
            DocumentScoringProps.SCORING_METHOD: ScoringMethodNames.EXACT,
            DocumentScoringProps.SCORING_TYPE: ScoringTypeNames.STRING,
            SummaryScoresProps.SUMMARY_SCORES: {
                'count': 1,
                'micro': scores,
                'macro': scores,
                'by-field': {
                    FIELD_1: {
                        'scores': scores,
                        'total': field_totals
                    }
                }
            }
        }]
        result = flatten_summary_results(
            summary_results, field_names=[FIELD_1]
        )
        LOGGER.debug('result: %s', result)
        assert len(result) > 1
        assert result[0] == {
            SummaryOutputColumns.DOCUMENT_COUNT: 1,
            SummaryOutputColumns.EVALUATION_METHOD: ScoringMethodNames.EXACT,
            SummaryOutputColumns.SCORING_TYPE: ScoringTypeNames.STRING,
            SummaryOutputColumns.FIELD_NAME: FIELD_1,
            SummaryOutputColumns.TP: field_totals[MatchScoringProps.TRUE_POSITIVE],
            SummaryOutputColumns.FP: field_totals[MatchScoringProps.FALSE_POSITIVE],
            SummaryOutputColumns.FN: field_totals[MatchScoringProps.FALSE_NEGATIVE],
            SummaryOutputColumns.TN: field_totals[MatchScoringProps.TRUE_NEGATIVE],
            SummaryOutputColumns.ACCURACY: scores['accuracy'],
            SummaryOutputColumns.PRECISION: scores['precision'],
            SummaryOutputColumns.RECALL: scores['recall'],
            SummaryOutputColumns.F1: scores['f1'],
            SummaryOutputColumns.JACCARD: scores['jaccard']
        }
        for stats_name, result_item in zip(['micro', 'macro'], result[1:]):
            assert result_item == {
                SummaryOutputColumns.DOCUMENT_COUNT: 1,
                SummaryOutputColumns.EVALUATION_METHOD: ScoringMethodNames.EXACT,
                SummaryOutputColumns.SCORING_TYPE: ScoringTypeNames.STRING,
                SummaryOutputColumns.STATS_NAME: stats_name,
                SummaryOutputColumns.ACCURACY: scores['accuracy'],
                SummaryOutputColumns.PRECISION: scores['precision'],
                SummaryOutputColumns.RECALL: scores['recall'],
                SummaryOutputColumns.F1: scores['f1'],
                SummaryOutputColumns.JACCARD: scores['jaccard']
            }


class TestGetAllSourceFieldNames:
    def test_should_return_none_if_passed_in_field_names_is_none(self):
        assert get_all_source_field_names(
            evaluation_config=EvaluationConfig(),
            field_names=None
        ) is None

    def test_should_return_passed_in_field_names_if_none_of_the_fields_match_custom_config(self):
        assert get_all_source_field_names(
            evaluation_config=EvaluationConfig(),
            field_names=[FIELD_1, FIELD_2]
        ) == [FIELD_1, FIELD_2]

    def test_should_add_source_fields_from_custom_config(self):
        assert sorted(get_all_source_field_names(
            evaluation_config=EvaluationConfig(
                custom=CustomEvaluationConfig(
                    fields=[CustomEvaluationFieldConfig(
                        name=FIELD_1,
                        evaluation_type='dummy',
                        expected=CustomEvaluationFieldSourceConfig(field_names=['expected1']),
                        actual=CustomEvaluationFieldSourceConfig(field_names=['actual1'])
                    )]
                )
            ),
            field_names=[FIELD_1, FIELD_2]
        )) == sorted([FIELD_1, FIELD_2, 'expected1', 'actual1'])

    def test_should_not_add_already_existing_fields_from_custom_config(self):
        assert sorted(get_all_source_field_names(
            evaluation_config=EvaluationConfig(
                custom=CustomEvaluationConfig(
                    fields=[CustomEvaluationFieldConfig(
                        name=FIELD_1,
                        evaluation_type='dummy',
                        expected=CustomEvaluationFieldSourceConfig(
                            field_names=['expected1', FIELD_1]
                        ),
                        actual=CustomEvaluationFieldSourceConfig(field_names=['actual1', FIELD_2])
                    )]
                )
            ),
            field_names=[FIELD_1]
        )) == sorted([FIELD_1, FIELD_2, 'expected1', 'actual1'])


class TestGetScoringTypesByFieldMap:
    def test_should_return_configured_scoring_types(self, temp_dir: Path):
        opt = get_default_args()
        opt.evaluation_config = str(temp_dir / 'evaluation.conf')
        Path(opt.evaluation_config).write_text('\n'.join([
            '[scoring_type]',
            'field1=old1',
            'field2=old2'
        ]))
        assert get_scoring_types_by_field_map(opt) == {
            'field1': ['old1'],
            'field2': ['old2']
        }

    def test_should_apply_scoring_type_overrides(self, temp_dir: Path):
        opt = get_default_args()
        opt.evaluation_config = str(temp_dir / 'evaluation.conf')
        opt.scoring_type_overrides = parse_scoring_type_overrides(
            'field1=new1.1,new1.2'
        )
        Path(opt.evaluation_config).write_text('\n'.join([
            '[scoring_type]',
            'field1=old1',
            'field2=old2'
        ]))
        assert get_scoring_types_by_field_map(opt) == {
            'field1': ['new1.1', 'new1.2'],
            'field2': ['old2']
        }


class TestParseArgs:
    def test_should_be_able_to_pass_fields(self):
        opt = parse_args(MIN_ARGV + [
            '--fields=+section_paragraphs,-reference_text'
        ])
        assert 'section_paragraphs' in opt.fields
        assert 'reference_text' not in opt.fields
        assert 'abstract' in opt.fields


@pytest.mark.slow
@pytest.mark.usefixtures('get_evaluation_config_mock')
class TestConfigurePipeline(BeamTest):
    def test_should_pass_pdf_file_list_and_limit_to_read_dict_csv_and_read_pdf_file(self):
        with patch_conversion_pipeline() as mocks:
            opt = get_default_args()
            opt.limit = 100

            mocks['load_file_list'].side_effect = load_file_list_side_effect(
                FILE_LIST_MAP
            )

            with TestPipeline() as p:
                configure_pipeline(p, opt)

            mocks['load_file_list'].assert_any_call(
                opt.target_file_list, column=opt.target_file_column, limit=opt.limit
            )
            mocks['load_file_list'].assert_any_call(
                opt.prediction_file_list, column=opt.target_file_column, limit=opt.limit
            )
            mocks['read_all_from_path'].assert_any_call(
                TARGET_FILE_LIST[0]
            )
            mocks['read_all_from_path'].assert_any_call(
                PREDICTION_FILE_LIST[0]
            )

    def test_should_pass_around_values_with_default_pipeline(
        self,
        get_evaluation_config_mock: MagicMock
    ):
        with patch_conversion_pipeline() as mocks:
            opt = get_default_args()

            mocks['load_file_list'].side_effect = load_file_list_side_effect(
                SINGLE_FILE_LIST_MAP
            )
            mocks['read_all_from_path'].side_effect = read_all_from_path_side_effect()

            with TestPipeline() as p:
                configure_pipeline(p, opt)

            mocks['evaluate_file_pairs'].assert_called_with(
                TARGET_FILE_LIST[0], dummy_file_content(TARGET_FILE_LIST[0]),
                PREDICTION_FILE_LIST[0], dummy_file_content(
                    PREDICTION_FILE_LIST[0]
                ),
                xml_mapping=mocks['parse_xml_mapping'].return_value,
                evaluation_config=get_evaluation_config_mock.return_value,
                scoring_types_by_field_map=get_scoring_types_by_field_map_from_config(
                    mocks['parse_evaluation_config'].return_value
                ),
                field_names=opt.fields,
                measures=opt.measures,
                convert_to_lower=opt.convert_to_lower
            )
