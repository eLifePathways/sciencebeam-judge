from __future__ import division
from functools import wraps
from typing import Callable, List, Union

from difflib import SequenceMatcher

import editdistance

from sciencebeam_judge.utils.typing import T

from ...utils.distance_matching import (
    T_Distance_Function,
    T_Optionally_Wrapped_Value,
    T_Value,
    DistanceMeasure,
    Value_Types,
    get_length_based_upper_bound_score,
    get_character_count_based_upper_bound_score,
    type_checked_distance_function
)

from ..normalization import (
    strip_punctuation_and_whitespace
)


class ScoringMethodNames:
    EXACT = 'exact'
    SOFT = 'soft'
    LEVENSHTEIN = 'levenshtein'
    RATCLIFF_OBERSHELP = 'ratcliff_obershelp'
    EDIT_SIM = 'edit_sim'


EDIT_DISTANCE_APPROXIMATE_FN_LIST = [
    get_length_based_upper_bound_score,
    get_character_count_based_upper_bound_score
]


def exact_score(expected: T_Value, actual: T_Value) -> float:
    return 1 if expected == actual else 0


def levenshtein_score(expected: T_Value, actual: T_Value) -> float:
    if not expected and not actual:
        return 1
    return 1 - (editdistance.eval(expected, actual) / max(len(expected), len(actual)))


def ratcliff_obershelp_score(expected: T_Value, actual: T_Value) -> float:
    return SequenceMatcher(None, expected, actual).ratio()


def IDENTITY_FN(x: T) -> T:
    return x


def wrap_scoring_function_with_preprocessing(
    scoring_fn: T_Distance_Function,
    preprocessing_fn: Callable[[str], str]
) -> T_Distance_Function:
    if preprocessing_fn is None or (preprocessing_fn == IDENTITY_FN):  # noqa pylint: disable=comparison-with-callable
        return scoring_fn

    @wraps(scoring_fn)
    def wrapped(
        value_1: T_Optionally_Wrapped_Value,
        value_2: T_Optionally_Wrapped_Value
    ) -> float:
        if value_1 and isinstance(value_1, str):
            value_1 = preprocessing_fn(value_1)
        if value_2 and isinstance(value_2, str):
            value_2 = preprocessing_fn(value_2)
        return scoring_fn(value_1, value_2)
    return wrapped


class ScoringMethod:
    def __init__(
            self,
            name: str,
            scoring_fn: T_Distance_Function,
            approximate_scoring_fn_list: List[T_Distance_Function] = None,
            threshold: float = 1,
            preprocessing_fn: Callable[[str], str] = None,
            continuous: bool = False):
        self.name = name
        self.scoring_fn = scoring_fn
        self.approximate_scoring_fn_list = approximate_scoring_fn_list or []
        self.threshold = threshold
        self.preprocessing_fn = preprocessing_fn or IDENTITY_FN
        self.continuous = continuous

    def wrap_with_preprocessing(
        self,
        scoring_fn: T_Distance_Function
    ) -> T_Distance_Function:
        return wrap_scoring_function_with_preprocessing(
            scoring_fn,
            self.preprocessing_fn
        )

    @property
    def distance_measure(self) -> DistanceMeasure:
        return DistanceMeasure(
            self.wrap_with_preprocessing(self.scoring_fn),
            approximate_distance_fn_list=[
                self.wrap_with_preprocessing(fn)
                for fn in self.approximate_scoring_fn_list
            ]
        )

    def __str__(self):
        return self.name

    def __repr__(self):
        return '%s(threshold=%.3f)' % (self.name, self.threshold)


SCORING_METHODS = [
    ScoringMethod(
        ScoringMethodNames.EXACT,
        type_checked_distance_function(
            exact_score,
            Value_Types
        )
    ),
    ScoringMethod(
        ScoringMethodNames.SOFT,
        type_checked_distance_function(
            exact_score,
            Value_Types
        ),
        preprocessing_fn=strip_punctuation_and_whitespace
    ),
    ScoringMethod(
        ScoringMethodNames.LEVENSHTEIN,
        type_checked_distance_function(
            levenshtein_score,
            Value_Types
        ),
        approximate_scoring_fn_list=EDIT_DISTANCE_APPROXIMATE_FN_LIST,
        threshold=0.8
    ),
    ScoringMethod(
        ScoringMethodNames.RATCLIFF_OBERSHELP,
        type_checked_distance_function(
            ratcliff_obershelp_score,
            Value_Types
        ),
        approximate_scoring_fn_list=EDIT_DISTANCE_APPROXIMATE_FN_LIST,
        threshold=0.95
    ),
    ScoringMethod(
        ScoringMethodNames.EDIT_SIM,
        type_checked_distance_function(
            levenshtein_score,
            Value_Types
        ),
        approximate_scoring_fn_list=EDIT_DISTANCE_APPROXIMATE_FN_LIST,
        preprocessing_fn=strip_punctuation_and_whitespace,
        continuous=True
    ),
]

ALL_SCORING_METHOD_NAMES = [
    sm.name for sm in SCORING_METHODS
]

SCORING_METHODS_MAP = {
    sm.name: sm for sm in SCORING_METHODS
}


def get_scoring_method(measure: Union[str, ScoringMethod]) -> ScoringMethod:
    if isinstance(measure, ScoringMethod):
        return measure
    return SCORING_METHODS_MAP[measure]


def get_scoring_methods(measures: List[str] = None) -> List[ScoringMethod]:
    if not measures:
        measures = ALL_SCORING_METHOD_NAMES
    return [get_scoring_method(measure) for measure in measures]
