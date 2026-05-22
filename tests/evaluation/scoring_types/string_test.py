from __future__ import division

import logging

from sciencebeam_judge.evaluation.math import is_close

from sciencebeam_judge.evaluation.scoring_types.string import STRING_SCORING_TYPE


LOGGING = logging.getLogger(__name__)

SOME_TEXT = 'test 123'


class TestStringScoringType:
    def test_should_score_list_for_exact_match(self):
        result = STRING_SCORING_TYPE.score([SOME_TEXT], [SOME_TEXT])
        assert result['exact']['score'] == 1
        assert result['soft']['score'] == 1
        assert result['levenshtein']['score'] == 1
        assert result['ratcliff_obershelp']['score'] == 1

    def test_should_score_list_for_partial_match_with_spaces(self):
        result = STRING_SCORING_TYPE.score(['a b'], ['ab'])
        assert result['exact']['score'] == 0
        assert result['soft']['score'] == 1
        assert is_close(result['levenshtein']['score'], 2 / 3)
        assert is_close(result['ratcliff_obershelp']['score'], 0.8)

    def test_should_not_convert_to_lower_if_disabled(self):
        result = STRING_SCORING_TYPE.score(
            ['Abc'], ['aBC'], include_values=True, convert_to_lower=False
        )
        assert result['exact']['expected'] == 'Abc'
        assert result['exact']['actual'] == 'aBC'

    def test_should_convert_to_lower_if_enabled(self):
        result = STRING_SCORING_TYPE.score(
            ['Abc'], ['aBC'], include_values=True, convert_to_lower=True
        )
        assert result['exact']['expected'] == 'abc'
        assert result['exact']['actual'] == 'abc'


class TestStringScoringTypeEditSim:
    def test_exact_match_gives_f1_one(self):
        result = STRING_SCORING_TYPE.score([SOME_TEXT], [SOME_TEXT])
        assert result['edit_sim']['sim_sum'] == 1.0
        assert result['edit_sim']['expected_count'] == 1
        assert result['edit_sim']['predicted_count'] == 1

    def test_partial_match_carries_continuous_similarity(self):
        result = STRING_SCORING_TYPE.score(['axb'], ['ayb'])
        assert is_close(result['edit_sim']['sim_sum'], 2 / 3)
        assert result['edit_sim']['expected_count'] == 1
        assert result['edit_sim']['predicted_count'] == 1

    def test_gold_present_predicted_absent_is_recall_penalty(self):
        result = STRING_SCORING_TYPE.score([SOME_TEXT], [''])
        assert result['edit_sim']['sim_sum'] == 0.0
        assert result['edit_sim']['expected_count'] == 1
        assert result['edit_sim']['predicted_count'] == 0

    def test_gold_absent_predicted_present_is_precision_penalty(self):
        result = STRING_SCORING_TYPE.score([''], [SOME_TEXT])
        assert result['edit_sim']['sim_sum'] == 0.0
        assert result['edit_sim']['expected_count'] == 0
        assert result['edit_sim']['predicted_count'] == 1

    def test_both_absent_is_neutral(self):
        result = STRING_SCORING_TYPE.score([''], [''])
        assert result['edit_sim']['sim_sum'] == 0.0
        assert result['edit_sim']['expected_count'] == 0
        assert result['edit_sim']['predicted_count'] == 0

    def test_preprocessing_strips_punctuation_and_whitespace_before_scoring(self):
        # both sides normalise to 'helloworld' → perfect match
        result = STRING_SCORING_TYPE.score(['hello, world!'], ['hello world'])
        assert result['edit_sim']['sim_sum'] == 1.0

    def test_include_values_stores_preprocessed_expected_and_actual(self):
        result = STRING_SCORING_TYPE.score(
            ['hello, world!'], ['hello world'], include_values=True
        )
        assert result['edit_sim']['expected'] == 'helloworld'
        assert result['edit_sim']['actual'] == 'helloworld'
