import logging

import numpy as np

from sciencebeam_judge.evaluation.document_scoring import DocumentScoringProps

from sciencebeam_judge.evaluation.metrics import (
    jaccard_index,
    recall_for_tp_fn
)

from sciencebeam_judge.evaluation.score_aggregation import (
    compact_scores,
    combine_scores,
    combine_and_compact_document_scores_with_count,
    summarise_binary_results,
    summarise_combined_document_scores_with_count,
    precision_for_tp_fp,
    f1_for_precision_recall,
    SummaryScoresProps
)


LOGGER = logging.getLogger(__name__)


TP_MATCH_SCORE = {
    'true_positive': 1,
    'false_positive': 0,
    'false_negative': 0
}


class TestCompactScores:
    def test_should_total_scores_by_key(self):
        scores = {
            'key1': [{
                'true_positive': 1,
                'false_positive': 0,
                'false_negative': 0
            }, {
                'true_positive': 0,
                'false_positive': 1,
                'false_negative': 0
            }],
            'key2': [{
                'true_positive': 1,
                'false_positive': 0,
                'false_negative': 1
            }]
        }
        result = compact_scores(scores)
        assert result == {
            'key1': {
                'true_positive': 1,
                'false_positive': 1,
                'false_negative': 0
            },
            'key2': {
                'true_positive': 1,
                'false_positive': 0,
                'false_negative': 1
            }
        }


class TestCombineScores:
    def test_should_combine_scores_by_key(self):
        list_of_scores = [{
            'key1': {
                'true_positive': 1,
                'false_positive': 0,
                'false_negative': 0
            }
        }, {
            'key1': {
                'true_positive': 0,
                'false_positive': 1,
                'false_negative': 0
            },
        }, {
            'key2': {
                'true_positive': 1,
                'false_positive': 0,
                'false_negative': 1
            }
        }]
        combined_scores = {
            'key1': [{
                'true_positive': 1,
                'false_positive': 0,
                'false_negative': 0
            }, {
                'true_positive': 0,
                'false_positive': 1,
                'false_negative': 0
            }],
            'key2': [{
                'true_positive': 1,
                'false_positive': 0,
                'false_negative': 1
            }]
        }
        result = combine_scores(list_of_scores)
        assert result == combined_scores


class TestCombineAndCompactDocumentScoresWithCount:
    def test_should_combine_single_score(self):
        document_scores_with_count = [([{
            DocumentScoringProps.FIELD_NAME: 'field1',
            DocumentScoringProps.SCORING_TYPE: 'string',
            DocumentScoringProps.SCORING_METHOD: 'exact',
            DocumentScoringProps.MATCH_SCORE: TP_MATCH_SCORE
        }], 1)]
        expected_combined_scores_with_count = ([{
            DocumentScoringProps.FIELD_NAME: 'field1',
            DocumentScoringProps.SCORING_TYPE: 'string',
            DocumentScoringProps.SCORING_METHOD: 'exact',
            DocumentScoringProps.MATCH_SCORE: TP_MATCH_SCORE
        }], 1)
        actual_combined_scores_with_count = combine_and_compact_document_scores_with_count(
            document_scores_with_count
        )
        LOGGER.debug(
            'expected_combined_scores_with_count: %s',
            expected_combined_scores_with_count
        )
        LOGGER.debug(
            'actual_combined_scores_with_count: %s',
            actual_combined_scores_with_count
        )
        assert actual_combined_scores_with_count == expected_combined_scores_with_count


class TestSummariseBinaryResults:
    def test_should_return_zero_results_for_no_values(self):
        scores = {
            'key1': []
        }
        result = summarise_binary_results(scores, keys=['key1'])
        key1_results = result.get('by-field', {}).get('key1', {})
        key1_totals = key1_results.get('total', {})
        assert key1_totals.get('true_positive') == 0
        assert key1_totals.get('false_positive') == 0
        assert key1_totals.get('false_negative') == 0
        assert key1_totals.get('true_negative') == 0

    def test_should_ignore_scores_not_in_specified_keys(self):
        scores = {
            'key1': [],
            'key2': []
        }
        result = summarise_binary_results(scores, keys=['key1'])
        assert set(result.get('by-field', {}).keys()) == {'key1'}

    def test_should_ignore_fields_without_a_score(self):
        scores = {
            'key1': []
        }
        result = summarise_binary_results(scores, keys=['key1', 'key2'])
        assert set(result.get('by-field', {}).keys()) == {'key1'}

    def test_should_return_sum_individual_counts_and_calculate_f1(self):
        scores = {
            'key1': [{
                'true_positive': 1,
                'false_positive': 0,
                'false_negative': 0
            }, {
                'true_positive': 0,
                'false_positive': 1,
                'false_negative': 0
            }]
        }
        result = summarise_binary_results(scores, keys=['key1'])
        key1_results = result.get('by-field', {}).get('key1', {})
        key1_totals = key1_results.get('total', {})
        key1_scores = key1_results.get('scores', {})
        assert key1_totals.get('true_positive') == 1
        assert key1_totals.get('false_positive') == 1
        assert key1_totals.get('false_negative') == 0
        assert key1_scores.get('precision') == 0.5
        assert key1_scores.get('recall') == 1.0
        assert key1_scores.get('jaccard') == 0.5
        assert key1_scores.get('f1') == f1_for_precision_recall(0.5, 1.0)
        # since there is no other field
        assert result.get('total') == key1_totals
        assert result.get('micro') == key1_scores
        assert result.get('macro') == key1_scores

    def test_should_return_calculate_f1_for_multiple_keys(self):
        scores = {
            'key1': [{
                'true_positive': 1,
                'false_positive': 1,
                'false_negative': 0
            }],
            'key2': [{
                'true_positive': 1,
                'false_positive': 0,
                'false_negative': 1
            }]
        }
        result = summarise_binary_results(scores, keys=['key1', 'key2'])
        key1_results = result.get('by-field', {}).get('key1', {})
        key1_totals = key1_results.get('total', {})
        key1_scores = key1_results.get('scores', {})
        micro_avg = result.get('micro', {})
        macro_avg = result.get('macro', {})
        assert key1_totals.get('true_positive') == 1
        assert key1_totals.get('false_positive') == 1
        assert key1_totals.get('false_negative') == 0
        assert key1_scores.get('precision') == 0.5
        assert key1_scores.get('recall') == 1.0
        assert key1_scores.get('jaccard') == 0.5
        assert key1_scores.get('f1') == f1_for_precision_recall(0.5, 1.0)

        key2_results = result.get('by-field', {}).get('key2', {})
        key2_totals = key2_results.get('total', {})
        key2_scores = key2_results.get('scores', {})
        assert key2_totals.get('true_positive') == 1
        assert key2_totals.get('false_positive') == 0
        assert key2_totals.get('false_negative') == 1
        assert key2_scores.get('precision') == 1.0
        assert key2_scores.get('recall') == 0.5
        assert key2_scores.get('f1') == f1_for_precision_recall(
            key2_scores.get('precision'),
            key2_scores.get('recall')
        )

        assert macro_avg.get('precision') == np.mean([
            key1_scores.get('precision'),
            key2_scores.get('precision')
        ])
        assert macro_avg.get('recall') == np.mean([
            key1_scores.get('recall'),
            key2_scores.get('recall')
        ])
        assert macro_avg.get('f1') == np.mean([
            key1_scores.get('f1'),
            key2_scores.get('f1')
        ])

        assert micro_avg.get('precision') == precision_for_tp_fp(
            key1_totals.get('true_positive') +
            key2_totals.get('true_positive'),
            key1_totals.get('false_positive') +
            key2_totals.get('false_positive')
        )
        total_tp = key1_totals.get('true_positive') + key2_totals.get('true_positive')
        total_fn = key1_totals.get('false_negative') + key2_totals.get('false_negative')
        total_fp = key1_totals.get('false_positive') + key2_totals.get('false_positive')
        assert micro_avg.get('recall') == recall_for_tp_fn(total_tp, total_fn)
        assert micro_avg.get('jaccard') == jaccard_index(total_tp, total_fn, total_fp)
        assert micro_avg.get('f1') == f1_for_precision_recall(
            micro_avg.get('precision'),
            micro_avg.get('recall')
        )


class TestSummariseCombinedDocumentScoresWithCount:
    def test_should_summarise_single_document_score(self):
        combined_scores_with_count = ([{
            DocumentScoringProps.FIELD_NAME: 'field1',
            DocumentScoringProps.SCORING_TYPE: 'string',
            DocumentScoringProps.SCORING_METHOD: 'exact',
            DocumentScoringProps.MATCH_SCORE: TP_MATCH_SCORE
        }], 1)
        actual_summary_scores = summarise_combined_document_scores_with_count(
            combined_scores_with_count, ['field1']
        )
        LOGGER.debug('actual_summary_scores: %s', actual_summary_scores)

        assert len(actual_summary_scores) == 1
        assert actual_summary_scores[0][DocumentScoringProps.SCORING_TYPE] == 'string'
        assert actual_summary_scores[0][DocumentScoringProps.SCORING_METHOD] == 'exact'

        summary_scores = actual_summary_scores[0][SummaryScoresProps.SUMMARY_SCORES]
        field1_summary_scores = summary_scores['by-field']['field1']['scores']
        assert field1_summary_scores['f1'] == 1
