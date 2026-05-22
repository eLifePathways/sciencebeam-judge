import logging
from abc import abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union

from sciencebeam_utils.utils.collection import extend_dict

from sciencebeam_judge.utils.typing import T

from ...utils.distance_matching import get_distance_matches

from ..math import safe_mean

from ..normalization import normalize_string

from ..scoring_methods.scoring_methods import ScoringMethod, get_scoring_methods

from ..match_scoring import (
    get_match_score_obj_for_score_fn,
    get_match_score_obj_for_score,
    get_match_score_obj_for_continuous_score,
    ContinuousMatchScoringProps,
    MatchScoringProps
)

from .scoring_type import ScoringType

from .items import wrap_items_scoring_methods, is_items_list, normalize_items_list


LOGGER = logging.getLogger(__name__)


def to_list(x):
    if isinstance(x, str):
        return {x}
    return list(x)


def normalize_string_or_list(
        value: Union[str, List[str]],
        **kwargs) -> Union[str, List[str]]:
    if isinstance(value, list):
        return normalize_list(value, **kwargs)
    return normalize_string(value, **kwargs)


def normalize_list(value, convert_to_lower=False):
    return [
        normalize_string_or_list(x, convert_to_lower=convert_to_lower)
        for x in value
    ]


def list_to_str(iterable):
    return ', '.join(str(x) for x in iterable)


def pad_list(
    list_: List[Optional[T]],
    desired_length: int,
    pad_value: T = None
) -> List[Optional[T]]:
    if len(list_) == desired_length:
        return list_
    assert desired_length > len(list_)
    return list_ + [pad_value] * (desired_length - len(list_))


def pad_longest(*lists: List[Optional[T]]) -> List[List[Optional[T]]]:
    max_len = max(len(list_) for list_ in lists)
    return [pad_list(list_, max_len) for list_ in lists]


def _sum_field(sequence, key):
    return sum(x[key] for x in sequence)


def _combine_partial_match_scores(scores, template_score):
    LOGGER.debug('_combine_partial_match_scores: %s', scores)
    return extend_dict(template_score, {
        MatchScoringProps.TRUE_POSITIVE: _sum_field(scores, MatchScoringProps.TRUE_POSITIVE),
        MatchScoringProps.FALSE_POSITIVE: _sum_field(scores, MatchScoringProps.FALSE_POSITIVE),
        MatchScoringProps.FALSE_NEGATIVE: _sum_field(scores, MatchScoringProps.FALSE_NEGATIVE),
        MatchScoringProps.TRUE_NEGATIVE: _sum_field(scores, MatchScoringProps.TRUE_NEGATIVE),
        MatchScoringProps.SUB_SCORES: scores
    })


def _combine_continuous_scores(
    scores: List[Dict[str, Any]],
    include_sub_scores: bool = False,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        ContinuousMatchScoringProps.SIM_SUM: sum(
            s[ContinuousMatchScoringProps.SIM_SUM] for s in scores
        ),
        ContinuousMatchScoringProps.EXPECTED_COUNT: sum(
            s[ContinuousMatchScoringProps.EXPECTED_COUNT] for s in scores
        ),
        ContinuousMatchScoringProps.PREDICTED_COUNT: sum(
            s[ContinuousMatchScoringProps.PREDICTED_COUNT] for s in scores
        ),
    }
    if include_sub_scores:
        result[MatchScoringProps.SUB_SCORES] = scores
    return result


def score_value_as_list_using_continuous_scoring_method(
    expected_list: List[Optional[str]],
    actual_list: List[Optional[str]],
    scoring_method: ScoringMethod,
    include_values: bool = False,
    partial: bool = False,
) -> Dict[str, Any]:
    if partial:
        expected_list, actual_list = pad_longest(expected_list, actual_list)
    else:
        if not expected_list and not actual_list:
            return get_match_score_obj_for_continuous_score('', '', 0.0)
        if len(expected_list) != len(actual_list):
            return {
                ContinuousMatchScoringProps.SIM_SUM: 0.0,
                ContinuousMatchScoringProps.EXPECTED_COUNT: len(expected_list),
                ContinuousMatchScoringProps.PREDICTED_COUNT: len(actual_list),
            }
    preprocessing_fn = scoring_method.preprocessing_fn
    scores: List[Dict[str, Any]] = []
    for expected_item, actual_item in zip(expected_list, actual_list):
        expected_val = expected_item or ''
        actual_val = actual_item or ''
        preprocessed_expected = preprocessing_fn(expected_val) if expected_val else expected_val
        preprocessed_actual = preprocessing_fn(actual_val) if actual_val else actual_val
        raw_score = scoring_method.scoring_fn(preprocessed_expected, preprocessed_actual)
        scores.append(get_match_score_obj_for_continuous_score(
            preprocessed_expected,
            preprocessed_actual,
            raw_score,
            include_values=include_values,
        ))
    return _combine_continuous_scores(scores, include_sub_scores=partial)


def score_value_as_unordered_list_using_continuous_scoring_method(
    expected_list: List,
    actual_list: List,
    scoring_method: ScoringMethod,
    include_values: bool = False,
    partial: bool = False,
) -> Dict[str, Any]:
    if not partial:
        if not expected_list and not actual_list:
            return get_match_score_obj_for_continuous_score('', '', 0.0)
        if len(expected_list) != len(actual_list):
            return {
                ContinuousMatchScoringProps.SIM_SUM: 0.0,
                ContinuousMatchScoringProps.EXPECTED_COUNT: len(expected_list),
                ContinuousMatchScoringProps.PREDICTED_COUNT: len(actual_list),
            }
    distance_measure = scoring_method.distance_measure
    match_results = get_distance_matches(
        expected_list,
        actual_list,
        distance_measure=distance_measure,
        threshold=0.0,
    )
    scores: List[Dict[str, Any]] = []
    for match_result in match_results:
        expected_val = match_result.value_1 or ''
        actual_val = match_result.value_2 or ''
        scores.append(get_match_score_obj_for_continuous_score(
            expected_val,
            actual_val,
            match_result.score,
            include_values=include_values,
        ))
    return _combine_continuous_scores(scores, include_sub_scores=partial)


def score_value_as_list_using_match_scoring_fn(
        expected_list, actual_list,
        expected_str, actual_str,
        match_scoring_fn, threshold,
        include_values=False, partial=False):
    # pylint: disable=too-many-locals

    def to_match_score(score):
        return get_match_score_obj_for_score(
            expected_str, actual_str, score,
            threshold=threshold, include_values=include_values
        )

    if partial:
        expected_list, actual_list = pad_longest(expected_list, actual_list)
    else:
        if not expected_list and not actual_list:
            LOGGER.debug('empty lists (expected and actual), 1.0 score')
            return to_match_score(1.0)
        if len(expected_list) != len(actual_list):
            LOGGER.debug(
                'number of items mismatch (expected=%d, actual=%d), 0.0 score',
                len(expected_list), len(actual_list)
            )
            return to_match_score(0.0)
    scores = []
    for expected_item, actual_item in zip(expected_list, actual_list):
        score = match_scoring_fn(
            expected_item,
            actual_item
        )

        if score['score'] < threshold and not partial:
            return to_match_score(0.0)

        scores.append(score)

    LOGGER.debug(
        'score_value_as_list_using_match_scoring_fn, partial=%s, scores=%s', partial, scores
    )
    mean_score = safe_mean([
        _score['score'] for _score in scores
    ]) if scores else 1.0
    result_score = to_match_score(mean_score)
    if partial:
        result_score = _combine_partial_match_scores(scores, result_score)
    return result_score


def score_value_as_list_using_scoring_method(
        expected_list, actual_list, scoring_method,
        include_values=False, partial=False):

    expected_str = list_to_str(expected_list)
    actual_str = list_to_str(actual_list)
    return score_value_as_list_using_match_scoring_fn(
        expected_list, actual_list,
        expected_str, actual_str,
        lambda expected_item, actual_item: get_match_score_obj_for_score_fn(
            expected_item or '',
            actual_item or '',
            scoring_method.scoring_fn,
            scoring_method.threshold,
            include_values=include_values
        ),
        scoring_method.threshold,
        include_values=include_values,
        partial=partial
    )


def score_value_as_unordered_list_using_scoring_method(
    expected_list: List[Union[str, Tuple[str]]],
    actual_list: List[Union[str, Tuple[str]]],
    scoring_method: ScoringMethod,
    include_values: bool = False,
    partial: bool = False
):
    def to_match_score(score):
        expected_str = list_to_str(expected_list)
        actual_str = list_to_str(actual_list)
        return get_match_score_obj_for_score(
            expected_str, actual_str, score,
            threshold=scoring_method.threshold, include_values=include_values
        )

    if not partial:
        if not expected_list and not actual_list:
            LOGGER.debug('empty lists (expected and actual), 1.0 score')
            return to_match_score(1.0)
        if len(expected_list) != len(actual_list):
            LOGGER.debug(
                'number of items mismatch (expected=%d, actual=%d), 0.0 score',
                len(expected_list), len(actual_list)
            )
            return to_match_score(0.0)

    distance_measure = scoring_method.distance_measure
    match_results = get_distance_matches(
        expected_list,
        actual_list,
        distance_measure=distance_measure,
        threshold=scoring_method.threshold
    )
    scores = []
    for match_result in match_results:
        scores.append(get_match_score_obj_for_score(
            match_result.value_1 or '',
            match_result.value_2 or '',
            match_result.score,
            threshold=scoring_method.threshold, include_values=include_values
        ))

    mean_score = safe_mean([score['score']
                            for score in scores]) if scores else 1.0
    LOGGER.debug(
        'returning list score (%s), mean_score=%.3f, scores=%s',
        scoring_method, mean_score, scores
    )
    result_score = to_match_score(mean_score)
    if partial:
        result_score = _combine_partial_match_scores(scores, result_score)
    return result_score


class ListScoringType(ScoringType):
    def __init__(self, partial=False):
        self.partial = partial

    @abstractmethod
    def _score_using_scoring_method(
            self, expected_list, actual_list, scoring_method,
            include_values=False, convert_to_lower=False):
        pass

    def score_items(
            self, expected_list, actual_list,
            include_values=False, measures=None, convert_to_lower=False):
        expected_list = normalize_items_list(
            expected_list, convert_to_lower=convert_to_lower)
        actual_list = normalize_items_list(
            actual_list, convert_to_lower=convert_to_lower)
        scoring_methods = wrap_items_scoring_methods(
            get_scoring_methods(measures=measures))
        scores = {}
        for scoring_method in scoring_methods:
            scores[scoring_method.name] = self._score_using_scoring_method(
                expected_list,
                actual_list,
                scoring_method,
                include_values=include_values,
                convert_to_lower=convert_to_lower
            )
        return scores

    def score_list(
            self, expected_list, actual_list,
            include_values=False, measures=None, convert_to_lower=False):
        expected_list = normalize_list(
            expected_list, convert_to_lower=convert_to_lower)
        actual_list = normalize_list(
            actual_list, convert_to_lower=convert_to_lower)
        scoring_methods = get_scoring_methods(measures=measures)
        scores = {}
        for scoring_method in scoring_methods:
            scores[scoring_method.name] = self._score_using_scoring_method(
                expected_list,
                actual_list,
                scoring_method,
                include_values=include_values,
                convert_to_lower=convert_to_lower
            )
        return scores

    def score(self, expected, actual, **kwargs):  # pylint: disable=arguments-differ
        expected_list = to_list(expected)
        actual_list = to_list(actual)
        if is_items_list(expected_list) or is_items_list(actual_list):
            return self.score_items(expected_list, actual_list, **kwargs)
        return self.score_list(expected_list, actual_list, **kwargs)


class OrderedListScoringType(ListScoringType):
    def _score_using_scoring_method(
            self, expected_list, actual_list, scoring_method,
            include_values=False, convert_to_lower=False):

        if scoring_method.continuous:
            return score_value_as_list_using_continuous_scoring_method(
                expected_list,
                actual_list,
                scoring_method,
                include_values=include_values,
                partial=self.partial,
            )
        return score_value_as_list_using_scoring_method(
            expected_list,
            actual_list,
            scoring_method,
            include_values=include_values,
            partial=self.partial
        )


class UnorderedListScoringType(ListScoringType):
    def _score_using_scoring_method(
            self, expected_list, actual_list, scoring_method,
            include_values=False, convert_to_lower=False):

        if scoring_method.continuous:
            return score_value_as_unordered_list_using_continuous_scoring_method(
                expected_list,
                actual_list,
                scoring_method,
                include_values=include_values,
                partial=self.partial,
            )
        return score_value_as_unordered_list_using_scoring_method(
            expected_list,
            actual_list,
            scoring_method,
            include_values=include_values,
            partial=self.partial
        )


def _to_hashable_item(item):
    if isinstance(item, list):
        return tuple(item)
    return item


def _to_hashable_items(items: list):
    return [_to_hashable_item(item) for item in items]


class SetScoringType(ListScoringType):
    def _score_using_scoring_method(
            self, expected_list, actual_list, scoring_method,
            include_values=False, convert_to_lower=False):

        deduped_expected = sorted(set(_to_hashable_items(expected_list)))
        deduped_actual = sorted(set(_to_hashable_items(actual_list)))
        if scoring_method.continuous:
            return score_value_as_unordered_list_using_continuous_scoring_method(
                deduped_expected,
                deduped_actual,
                scoring_method,
                include_values=include_values,
                partial=self.partial,
            )
        return score_value_as_unordered_list_using_scoring_method(
            deduped_expected,
            deduped_actual,
            scoring_method,
            include_values=include_values,
            partial=self.partial
        )


ORDERED_LIST_SCORING_TYPE = OrderedListScoringType()
PARTIAL_ORDERED_LIST_SCORING_TYPE = OrderedListScoringType(partial=True)

UNORDERED_LIST_SCORING_TYPE = UnorderedListScoringType()
PARTIAL_UNORDERED_LIST_SCORING_TYPE = UnorderedListScoringType(partial=True)

SET_SCORING_TYPE = SetScoringType()
PARTIAL_SET_SCORING_TYPE = SetScoringType(partial=True)
