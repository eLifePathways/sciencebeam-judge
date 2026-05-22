from ..normalization import normalize_whitespace

from ..scoring_methods.scoring_methods import get_scoring_methods

from ..match_scoring import (
    get_match_score_obj_for_score_fn,
    get_match_score_obj_for_continuous_score,
)

from .scoring_type import ScoringType


class StringScoringType(ScoringType):
    def score(self, expected, actual, include_values=False, measures=None, convert_to_lower=False):
        # sep = '\n'
        sep = ''
        expected_str = normalize_whitespace(sep.join(expected))
        actual_str = normalize_whitespace(sep.join(actual))
        if convert_to_lower:
            expected_str = expected_str.lower()
            actual_str = actual_str.lower()
        scores = {}
        scoring_methods = get_scoring_methods(measures=measures)
        for scoring_method in scoring_methods:
            preprocessed_expected = scoring_method.preprocessing_fn(expected_str)
            preprocessed_actual = scoring_method.preprocessing_fn(actual_str)
            if scoring_method.continuous:
                raw_score = scoring_method.scoring_fn(preprocessed_expected, preprocessed_actual)
                scores[scoring_method.name] = get_match_score_obj_for_continuous_score(
                    preprocessed_expected,
                    preprocessed_actual,
                    raw_score,
                    include_values=include_values,
                )
            else:
                scores[scoring_method.name] = get_match_score_obj_for_score_fn(
                    preprocessed_expected,
                    preprocessed_actual,
                    scoring_method.scoring_fn,
                    threshold=scoring_method.threshold,
                    include_values=include_values
                )
        if not scores:
            raise AttributeError('no measures calculated')
        return scores


STRING_SCORING_TYPE = StringScoringType()
