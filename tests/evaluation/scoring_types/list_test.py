from __future__ import division

import logging

from abc import ABC, abstractmethod

from sciencebeam_judge.evaluation.math import is_close
from sciencebeam_judge.evaluation.match_scoring import (
    ContinuousMatchScoringProps,
    MatchScoringProps,
)
from sciencebeam_judge.evaluation.scoring_methods.scoring_methods import ScoringMethodNames

from sciencebeam_judge.evaluation.scoring_types.list import (
    ORDERED_LIST_SCORING_TYPE,
    PARTIAL_ORDERED_LIST_SCORING_TYPE,
    UNORDERED_LIST_SCORING_TYPE,
    PARTIAL_UNORDERED_LIST_SCORING_TYPE,
    SET_SCORING_TYPE,
    PARTIAL_SET_SCORING_TYPE
)


LOGGING = logging.getLogger(__name__)

SOME_TEXT = 'test 123'

ALMOST_MATCHING_TEXTS = [
    'This almost matches',
    'This almost matched'
]


class _TestCommonListScoringType(ABC):
    @abstractmethod
    def score(self, *args, **kwargs):
        pass

    def test_should_match_if_items_match_in_same_order(self):
        result = self.score(['a', 'b'], ['a', 'b'])
        LOGGING.debug('result: %s', result)
        assert result['exact']['score'] == 1
        assert result['soft']['score'] == 1
        assert result['levenshtein']['score'] == 1
        assert result['ratcliff_obershelp']['score'] == 1

    def test_should_match_empty_lists(self):
        result = self.score([], [])
        LOGGING.debug('result: %s', result)
        assert result['exact']['score'] == 1

    def test_should_not_match_different_values(self):
        result = self.score(['a'], ['b'])
        LOGGING.debug('result: %s', result)
        assert result['exact']['score'] == 0

    def test_should_normalize_space(self):
        result = self.score(['a  b'], ['a b'])
        LOGGING.debug('result: %s', result)
        assert result['exact']['score'] == 1

    def test_should_convert_to_lower_if_enabled(self):
        result = self.score(['a', 'B'], ['A', 'b'], convert_to_lower=True)
        LOGGING.debug('result: %s', result)
        assert result['exact']['score'] == 1

    def test_should_not_convert_to_lower_if_not_enabled(self):
        result = self.score(['a', 'B'], ['A', 'b'], convert_to_lower=False)
        LOGGING.debug('result: %s', result)
        assert result['exact']['score'] == 0

    def test_should_allow_almost_matching_text(self):
        result = self.score(
            [ALMOST_MATCHING_TEXTS[0]],
            [ALMOST_MATCHING_TEXTS[1]]
        )
        LOGGING.debug('result: %s', result)
        assert result['exact'][MatchScoringProps.SCORE] == 0
        assert result['exact'][MatchScoringProps.TRUE_POSITIVE] == 0
        assert result['levenshtein'][MatchScoringProps.SCORE] > 0
        assert result['levenshtein'][MatchScoringProps.TRUE_POSITIVE] == 1


class _TestCommonNonPartialListScoringType(_TestCommonListScoringType):
    # pylint: disable=abstract-method

    def test_should_not_match_with_missing_value(self):
        result = self.score(['a', 'b'], ['a'])
        LOGGING.debug('result: %s', result)
        assert result['exact']['score'] == 0

    def test_should_not_match_with_extra_value(self):
        result = self.score(['a'], ['a', 'b'])
        LOGGING.debug('result: %s', result)
        assert result['exact']['score'] == 0


class _TestCommonPartialListScoringType(_TestCommonListScoringType):
    # pylint: disable=abstract-method

    def test_should_partially_match_with_missing_value(self):
        result = self.score(['a', 'b'], ['a'], measures=['exact'])
        LOGGING.debug('result: %s', result)
        assert result['exact'][MatchScoringProps.TRUE_POSITIVE] == 1
        assert result['exact'][MatchScoringProps.FALSE_NEGATIVE] == 1
        assert result['exact'][MatchScoringProps.SCORE] == 0.5

    def test_should_partially_match_with_extra_value(self):
        result = self.score(['a'], ['a', 'b'], measures=['exact'])
        LOGGING.debug('result: %s', result)
        assert result['exact'][MatchScoringProps.TRUE_POSITIVE] == 1
        assert result['exact'][MatchScoringProps.FALSE_POSITIVE] == 1
        assert result['exact'][MatchScoringProps.SCORE] == 0.5

    def test_should_include_sub_scores(self):
        result = self.score(['a', 'b'], ['a'], measures=['exact'])
        LOGGING.debug('result: %s', result)
        assert result['exact'][MatchScoringProps.SUB_SCORES][0][MatchScoringProps.SCORE] == 1.0
        assert result['exact'][MatchScoringProps.SUB_SCORES][1][MatchScoringProps.SCORE] == 0.0

    def test_should_include_expected_values_for_sub_scores(self):
        result = self.score(
            ['a', 'b'], ['a'], measures=['exact'], include_values=True
        )
        LOGGING.debug('result: %s', result)
        assert result['exact'][MatchScoringProps.SUB_SCORES][0][MatchScoringProps.EXPECTED] == 'a'
        assert result['exact'][MatchScoringProps.SUB_SCORES][1][MatchScoringProps.EXPECTED] == 'b'

    def test_should_include_sub_scores_for_empty_list(self):
        result = self.score([], [], measures=['exact'])
        LOGGING.debug('result: %s', result)
        assert result['exact'][MatchScoringProps.SUB_SCORES] == []

    def test_should_include_zero_tp_fp_fn_tn_for_empty_list(self):
        result = self.score([], [], measures=['exact'])
        LOGGING.debug('result: %s', result)
        assert result['exact'][MatchScoringProps.TRUE_POSITIVE] == 0
        assert result['exact'][MatchScoringProps.FALSE_POSITIVE] == 0
        assert result['exact'][MatchScoringProps.FALSE_NEGATIVE] == 0
        assert result['exact'][MatchScoringProps.TRUE_NEGATIVE] == 0


class TestOrderedListScoringType(_TestCommonNonPartialListScoringType):
    def score(self, *args, **kwargs):
        return ORDERED_LIST_SCORING_TYPE.score(*args, **kwargs)

    def test_should_not_match_different_order(self):
        result = self.score(['a', 'b'], ['b', 'a'])
        LOGGING.debug('result: %s', result)
        assert result['exact']['score'] == 0

    def test_should_match_multiple_items_to_single_text(self):
        result = self.score([{
            'items': ['ab']
        }], [{
            'items': ['b', 'a']
        }])
        LOGGING.debug('result: %s', result)
        assert result[ScoringMethodNames.EXACT]['score'] == 1

    def test_should_match_multiple_mostly_similar_items_to_single_text(self):
        result = self.score([{
            'items': ['%s%s' % (ALMOST_MATCHING_TEXTS[0], 'other')]
        }], [{
            'items': [ALMOST_MATCHING_TEXTS[1], 'other']
        }])
        LOGGING.debug('result: %s', result)
        assert result[ScoringMethodNames.EXACT]['score'] == 0
        assert result[ScoringMethodNames.LEVENSHTEIN]['score'] > 0

    def test_should_convert_items_to_lower_if_enabled(self):
        result = self.score([{
            'items': ['a', 'B']
        }], [{
            'items': ['A', 'b']
        }], convert_to_lower=True)
        LOGGING.debug('result: %s', result)
        assert result['exact']['score'] == 1

    def test_should_not_convert_items_to_lower_if_not_enabled(self):
        result = self.score([{
            'items': ['a', 'B']
        }], [{
            'items': ['A', 'b']
        }], convert_to_lower=False)
        LOGGING.debug('result: %s', result)
        assert result['exact']['score'] == 0


class TestPartialOrderedListScoringType(_TestCommonPartialListScoringType):
    def score(self, *args, **kwargs):
        return PARTIAL_ORDERED_LIST_SCORING_TYPE.score(*args, **kwargs)

    def test_should_include_actual_values_for_sub_scores(self):
        result = self.score(
            ['a', 'b'], ['a'], measures=['exact'], include_values=True
        )
        LOGGING.debug('result: %s', result)
        assert result['exact'][MatchScoringProps.SUB_SCORES][0][MatchScoringProps.ACTUAL] == 'a'
        assert result['exact'][MatchScoringProps.SUB_SCORES][1][MatchScoringProps.ACTUAL] == ''


class TestUnorderedListScoringType(_TestCommonNonPartialListScoringType):
    def score(self, *args, **kwargs):
        return UNORDERED_LIST_SCORING_TYPE.score(*args, **kwargs)

    def test_should_match_different_order(self):
        result = self.score(['a', 'b'], ['b', 'a'])
        LOGGING.debug('result: %s', result)
        assert result['exact']['score'] == 1

    def test_should_not_match_with_duplicate_expected_values(self):
        result = self.score(['a', 'a', 'b'], ['a', 'b'])
        LOGGING.debug('result: %s', result)
        assert result['exact']['score'] == 0

    def test_should_not_match_with_duplicate_actual_values(self):
        result = self.score(['a', 'b'], ['a', 'a', 'b'])
        LOGGING.debug('result: %s', result)
        assert result['exact']['score'] == 0


class TestPartialUnorderedListScoringType(_TestCommonPartialListScoringType):
    def score(self, *args, **kwargs):
        return PARTIAL_UNORDERED_LIST_SCORING_TYPE.score(*args, **kwargs)

    def test_should_count_mismatch_only_once(self):
        result = self.score(['a', 'b'], ['a', 'c'])
        LOGGING.debug('result: %s', result)
        assert len(result['exact'][MatchScoringProps.SUB_SCORES]) == 2
        assert result['exact'][MatchScoringProps.SCORE] == 0.5

    def test_should_pair_unmatch_with_closest_match(self):
        result = self.score(
            ['a', 'b1', 'c1'], ['a', 'c2', 'b2'],
            measures=[ScoringMethodNames.LEVENSHTEIN], include_values=True
        )
        LOGGING.debug('result: %s', result)
        sub_scores = result[ScoringMethodNames.LEVENSHTEIN][MatchScoringProps.SUB_SCORES]
        assert len(sub_scores) == 3
        assert {
            (score[MatchScoringProps.EXPECTED],
             score[MatchScoringProps.ACTUAL])
            for score in sub_scores
        } == {('a', 'a'), ('b1', 'b2'), ('c1', 'c2')}


class TestSetScoringType(_TestCommonNonPartialListScoringType):
    def score(self, *args, **kwargs):
        return SET_SCORING_TYPE.score(*args, **kwargs)

    def test_should_match_different_order(self):
        result = self.score(['a', 'b'], ['b', 'a'])
        LOGGING.debug('result: %s', result)
        assert result['exact']['score'] == 1

    def test_should_match_list_items_in_different_order(self):
        result = self.score([['a'], ['b']], [['b'], ['a']])
        LOGGING.debug('result: %s', result)
        assert result['exact']['score'] == 1

    def test_should_match_with_duplicate_expected_values(self):
        result = self.score(['a', 'a', 'b'], ['a', 'b'])
        LOGGING.debug('result: %s', result)
        assert result['exact']['score'] == 1

    def test_should_match_with_duplicate_actual_values(self):
        result = self.score(['a', 'b'], ['a', 'a', 'b'])
        LOGGING.debug('result: %s', result)
        assert result['exact']['score'] == 1


class TestPartialSetScoringType(_TestCommonPartialListScoringType):
    def score(self, *args, **kwargs):
        return PARTIAL_SET_SCORING_TYPE.score(*args, **kwargs)


EDIT_SIM = ScoringMethodNames.EDIT_SIM
C = ContinuousMatchScoringProps


class TestOrderedListScoringTypeEditSim:
    def score(self, *args, **kwargs):
        return ORDERED_LIST_SCORING_TYPE.score(*args, measures=[EDIT_SIM], **kwargs)

    def test_both_empty_is_neutral(self):
        result = self.score([], [])
        assert result[EDIT_SIM][C.SIM_SUM] == 0.0
        assert result[EDIT_SIM][C.EXPECTED_COUNT] == 0
        assert result[EDIT_SIM][C.PREDICTED_COUNT] == 0

    def test_length_mismatch_expected_longer_is_hard_f1_zero(self):
        result = self.score(['a', 'b'], ['a'])
        assert result[EDIT_SIM][C.SIM_SUM] == 0.0
        assert result[EDIT_SIM][C.EXPECTED_COUNT] == 2
        assert result[EDIT_SIM][C.PREDICTED_COUNT] == 1

    def test_length_mismatch_actual_longer_is_hard_f1_zero(self):
        result = self.score(['a'], ['a', 'b'])
        assert result[EDIT_SIM][C.SIM_SUM] == 0.0
        assert result[EDIT_SIM][C.EXPECTED_COUNT] == 1
        assert result[EDIT_SIM][C.PREDICTED_COUNT] == 2

    def test_exact_match_single_item(self):
        result = self.score(['abc'], ['abc'])
        assert result[EDIT_SIM][C.SIM_SUM] == 1.0
        assert result[EDIT_SIM][C.EXPECTED_COUNT] == 1
        assert result[EDIT_SIM][C.PREDICTED_COUNT] == 1

    def test_exact_match_multiple_items(self):
        result = self.score(['a', 'b'], ['a', 'b'])
        assert result[EDIT_SIM][C.SIM_SUM] == 2.0
        assert result[EDIT_SIM][C.EXPECTED_COUNT] == 2
        assert result[EDIT_SIM][C.PREDICTED_COUNT] == 2

    def test_partial_similarity_accumulates_sim_sum(self):
        # levenshtein_score('axb', 'ayb') = 1 - 1/3 = 2/3
        result = self.score(['axb'], ['ayb'])
        assert is_close(result[EDIT_SIM][C.SIM_SUM], 2 / 3)
        assert result[EDIT_SIM][C.EXPECTED_COUNT] == 1
        assert result[EDIT_SIM][C.PREDICTED_COUNT] == 1


class TestPartialOrderedListScoringTypeEditSim:
    def score(self, *args, **kwargs):
        return PARTIAL_ORDERED_LIST_SCORING_TYPE.score(*args, measures=[EDIT_SIM], **kwargs)

    def test_both_empty_is_neutral(self):
        result = self.score([], [])
        assert result[EDIT_SIM][C.SIM_SUM] == 0.0
        assert result[EDIT_SIM][C.EXPECTED_COUNT] == 0
        assert result[EDIT_SIM][C.PREDICTED_COUNT] == 0
        assert result[EDIT_SIM][MatchScoringProps.SUB_SCORES] == []

    def test_expected_longer_gives_recall_penalty(self):
        # expected=['a','b'], actual=['a'] → item1 sim=1.0 (D), item2 Case B
        result = self.score(['a', 'b'], ['a'])
        assert result[EDIT_SIM][C.SIM_SUM] == 1.0
        assert result[EDIT_SIM][C.EXPECTED_COUNT] == 2
        assert result[EDIT_SIM][C.PREDICTED_COUNT] == 1

    def test_actual_longer_gives_precision_penalty(self):
        # expected=['a'], actual=['a','b'] → item1 sim=1.0 (D), item2 Case C
        result = self.score(['a'], ['a', 'b'])
        assert result[EDIT_SIM][C.SIM_SUM] == 1.0
        assert result[EDIT_SIM][C.EXPECTED_COUNT] == 1
        assert result[EDIT_SIM][C.PREDICTED_COUNT] == 2

    def test_includes_sub_scores(self):
        result = self.score(['a', 'b'], ['a'])
        sub_scores = result[EDIT_SIM][MatchScoringProps.SUB_SCORES]
        assert len(sub_scores) == 2
        assert sub_scores[0][C.SIM_SUM] == 1.0
        assert sub_scores[0][C.EXPECTED_COUNT] == 1
        assert sub_scores[0][C.PREDICTED_COUNT] == 1
        assert sub_scores[1][C.SIM_SUM] == 0.0
        assert sub_scores[1][C.EXPECTED_COUNT] == 1
        assert sub_scores[1][C.PREDICTED_COUNT] == 0

    def test_include_values_stores_per_item_values(self):
        result = self.score(['a', 'b'], ['a'], include_values=True)
        sub_scores = result[EDIT_SIM][MatchScoringProps.SUB_SCORES]
        assert sub_scores[0][MatchScoringProps.EXPECTED] == 'a'
        assert sub_scores[0][MatchScoringProps.ACTUAL] == 'a'
        assert sub_scores[1][MatchScoringProps.EXPECTED] == 'b'
        assert sub_scores[1][MatchScoringProps.ACTUAL] == ''


class TestUnorderedListScoringTypeEditSim:
    def score(self, *args, **kwargs):
        return UNORDERED_LIST_SCORING_TYPE.score(*args, measures=[EDIT_SIM], **kwargs)

    def test_both_empty_is_neutral(self):
        result = self.score([], [])
        assert result[EDIT_SIM][C.SIM_SUM] == 0.0
        assert result[EDIT_SIM][C.EXPECTED_COUNT] == 0
        assert result[EDIT_SIM][C.PREDICTED_COUNT] == 0

    def test_length_mismatch_is_hard_f1_zero(self):
        result = self.score(['a', 'b'], ['a'])
        assert result[EDIT_SIM][C.SIM_SUM] == 0.0
        assert result[EDIT_SIM][C.EXPECTED_COUNT] == 2
        assert result[EDIT_SIM][C.PREDICTED_COUNT] == 1

    def test_exact_match_gives_full_similarity(self):
        result = self.score(['a', 'b'], ['a', 'b'])
        assert result[EDIT_SIM][C.SIM_SUM] == 2.0
        assert result[EDIT_SIM][C.EXPECTED_COUNT] == 2
        assert result[EDIT_SIM][C.PREDICTED_COUNT] == 2

    def test_different_order_gives_same_similarity(self):
        result_in_order = self.score(['a', 'b'], ['a', 'b'])
        result_reordered = self.score(['a', 'b'], ['b', 'a'])
        assert result_in_order[EDIT_SIM][C.SIM_SUM] == result_reordered[EDIT_SIM][C.SIM_SUM]
        assert result_reordered[EDIT_SIM][C.EXPECTED_COUNT] == 2
        assert result_reordered[EDIT_SIM][C.PREDICTED_COUNT] == 2


class TestPartialUnorderedListScoringTypeEditSim:
    def score(self, *args, **kwargs):
        return PARTIAL_UNORDERED_LIST_SCORING_TYPE.score(*args, measures=[EDIT_SIM], **kwargs)

    def test_expected_longer_gives_recall_penalty(self):
        result = self.score(['a', 'b'], ['a'])
        assert result[EDIT_SIM][C.SIM_SUM] == 1.0
        assert result[EDIT_SIM][C.EXPECTED_COUNT] == 2
        assert result[EDIT_SIM][C.PREDICTED_COUNT] == 1

    def test_actual_longer_gives_precision_penalty(self):
        result = self.score(['a'], ['a', 'b'])
        assert result[EDIT_SIM][C.SIM_SUM] == 1.0
        assert result[EDIT_SIM][C.EXPECTED_COUNT] == 1
        assert result[EDIT_SIM][C.PREDICTED_COUNT] == 2

    def test_includes_sub_scores(self):
        result = self.score(['a', 'b'], ['a'])
        sub_scores = result[EDIT_SIM][MatchScoringProps.SUB_SCORES]
        assert len(sub_scores) == 2

    def test_both_empty_is_neutral(self):
        result = self.score([], [])
        assert result[EDIT_SIM][C.SIM_SUM] == 0.0
        assert result[EDIT_SIM][C.EXPECTED_COUNT] == 0
        assert result[EDIT_SIM][C.PREDICTED_COUNT] == 0
