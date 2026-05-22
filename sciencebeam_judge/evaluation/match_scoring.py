from dataclasses import dataclass
from typing import Any, AnyStr, Dict, List, Optional, Union


T_Value = Union[AnyStr, List[AnyStr]]


class MatchScoringProps:
    EXPECTED_SOMETHING = 'expected_something'
    ACTUAL_SOMETHING = 'actual_something'
    SCORE = 'score'
    TRUE_POSITIVE = 'true_positive'
    TRUE_NEGATIVE = 'true_negative'
    FALSE_POSITIVE = 'false_positive'
    FALSE_NEGATIVE = 'false_negative'
    BINARY_EXPECTED = 'binary_expected'
    BINARY_ACTUAL = 'binary_actual'
    EXPECTED = 'expected'
    ACTUAL = 'actual'
    EXPECTED_CONTEXT = 'expected_context'
    ACTUAL_CONTEXT = 'actual_context'
    SUB_SCORES = 'sub_scores'


@dataclass
class MatchScore:  # pylint: disable=too-many-instance-attributes
    score: float
    expected_something: bool = True
    actual_something: bool = True
    true_positive: int = 0
    true_negative: int = 0
    false_positive: int = 0
    false_negative: int = 0
    binary_expected: int = 0
    binary_actual: int = 0
    expected: Optional[T_Value] = None
    actual: Optional[T_Value] = None
    expected_context: Optional[T_Value] = None
    actual_context: Optional[T_Value] = None
    sub_scores: Optional[List['MatchScore']] = None

    def to_dict(self) -> Dict[str, Any]:
        props = vars(self)
        if self.sub_scores:
            props = {
                **props,
                MatchScoringProps.SUB_SCORES: [
                    score.to_dict()
                    for score in self.sub_scores
                ]
            }
        return props

    @staticmethod
    def from_dict(match_score_dict: Dict[str, Any]) -> 'MatchScore':
        if match_score_dict.get(MatchScoringProps.SUB_SCORES):
            match_score_dict = {
                **match_score_dict,
                MatchScoringProps.SUB_SCORES: [
                    MatchScore.from_dict(score)
                    for score in match_score_dict[MatchScoringProps.SUB_SCORES]
                ]
            }
        return MatchScore(**match_score_dict)


def get_match_score_obj_for_score(
    expected: T_Value,
    actual: T_Value,
    score: float,
    threshold: float = 1.0,
    include_values: bool = False,
    expected_context: Optional[T_Value] = None,
    actual_context: Optional[T_Value] = None
):
    binary_expected = 1 if expected else 0
    # actual will be a false positive (1) if it is populated but expected is not,
    # otherwise it will be positive if it meets the threshold
    binary_actual = (
        1
        if actual and (binary_expected == 0 or (binary_expected == 1 and score >= threshold))
        else 0
    )
    tp = 1 if actual and expected and score >= threshold else 0
    tn = 1 if not actual and not expected else 0
    fp = 1 if not tp and actual else 0
    fn = 1 if not tn and not actual else 0
    d: Dict[str, Any] = {
        MatchScoringProps.EXPECTED_SOMETHING: len(expected) > 0,
        MatchScoringProps.ACTUAL_SOMETHING: len(actual) > 0,
        MatchScoringProps.SCORE: score,
        MatchScoringProps.TRUE_POSITIVE: tp,
        MatchScoringProps.TRUE_NEGATIVE: tn,
        MatchScoringProps.FALSE_POSITIVE: fp,
        MatchScoringProps.FALSE_NEGATIVE: fn,
        MatchScoringProps.BINARY_EXPECTED: binary_expected,
        MatchScoringProps.BINARY_ACTUAL: binary_actual
    }
    if include_values:
        d[MatchScoringProps.EXPECTED] = expected
        d[MatchScoringProps.ACTUAL] = actual
        d[MatchScoringProps.EXPECTED_CONTEXT] = expected_context
        d[MatchScoringProps.ACTUAL_CONTEXT] = actual_context
    return d


def get_match_score_for_score(*args, **kwargs) -> MatchScore:
    return MatchScore.from_dict(get_match_score_obj_for_score(*args, **kwargs))


def get_match_score_obj_for_score_fn(expected, actual, value_f, threshold=1, include_values=False):
    return get_match_score_obj_for_score(
        expected, actual,
        value_f(expected, actual),
        threshold=threshold, include_values=include_values
    )


class ContinuousMatchScoringProps:
    SIM_SUM = 'sim_sum'
    EXPECTED_COUNT = 'expected_count'
    PREDICTED_COUNT = 'predicted_count'


def get_match_score_obj_for_continuous_score(
    expected: T_Value,
    actual: T_Value,
    score: float,
    include_values: bool = False,
) -> Dict[str, Any]:
    """Return a continuous match score dict encoding similarity as sum/count fields.

    Unlike the binary encoding, this preserves partial similarity rather than
    collapsing it to a threshold pass/fail. The four cases:
      A) both absent  → neutral (no contribution)
      B) gold present, prediction absent  → recall penalty
      C) gold absent, prediction present  → precision penalty (possible hallucination)
      D) both present → contribute sim to sim_sum and both counts
    """
    if not expected and not actual:
        d: Dict[str, Any] = {
            ContinuousMatchScoringProps.SIM_SUM: 0.0,
            ContinuousMatchScoringProps.EXPECTED_COUNT: 0,
            ContinuousMatchScoringProps.PREDICTED_COUNT: 0,
        }
    elif expected and not actual:
        d = {
            ContinuousMatchScoringProps.SIM_SUM: 0.0,
            ContinuousMatchScoringProps.EXPECTED_COUNT: 1,
            ContinuousMatchScoringProps.PREDICTED_COUNT: 0,
        }
    elif not expected and actual:
        d = {
            ContinuousMatchScoringProps.SIM_SUM: 0.0,
            ContinuousMatchScoringProps.EXPECTED_COUNT: 0,
            ContinuousMatchScoringProps.PREDICTED_COUNT: 1,
        }
    else:
        d = {
            ContinuousMatchScoringProps.SIM_SUM: score,
            ContinuousMatchScoringProps.EXPECTED_COUNT: 1,
            ContinuousMatchScoringProps.PREDICTED_COUNT: 1,
        }
    if include_values:
        d[MatchScoringProps.EXPECTED] = expected
        d[MatchScoringProps.ACTUAL] = actual
    return d
