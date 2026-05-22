from __future__ import division

import logging

from sciencebeam_judge.evaluation.scoring_methods.scoring_methods import (
    exact_score,
    levenshtein_score,
    ratcliff_obershelp_score,
    ScoringMethodNames,
    get_scoring_method,
)

from sciencebeam_judge.evaluation.math import is_close


LOGGING = logging.getLogger(__name__)

SOME_TEXT = 'test 123'


class TestExactScore:
    def test_should_return_one_for_exact_match(self):
        assert exact_score(SOME_TEXT, SOME_TEXT) == 1

    def test_should_return_zero_for_any_mismatch(self):
        assert exact_score(SOME_TEXT, SOME_TEXT[:-1] + 'X') == 0


class TestLevenshteinScore:
    def test_should_return_one_for_exact_match(self):
        assert levenshtein_score(SOME_TEXT, SOME_TEXT) == 1

    def test_should_return_two_third_for_a_two_third_match(self):
        assert is_close(levenshtein_score('axb', 'ayb'), 2 / 3)

    def test_should_return_zero_for_no_match(self):
        assert levenshtein_score('abc', 'xyz') == 0


class TestRatcliffObershelpScore:
    def test_should_return_one_for_exact_match(self):
        assert ratcliff_obershelp_score(SOME_TEXT, SOME_TEXT) == 1

    def test_should_return_0666_for_a_two_third_match(self):
        assert is_close(ratcliff_obershelp_score('axb', 'ayb'), 2 / 3)

    def test_should_return_zero_for_no_match(self):
        assert ratcliff_obershelp_score('abc', 'xyz') == 0


class TestEditSimScoringMethod:
    def test_is_marked_as_continuous(self):
        method = get_scoring_method(ScoringMethodNames.EDIT_SIM)
        assert method.continuous is True

    def test_has_no_threshold(self):
        method = get_scoring_method(ScoringMethodNames.EDIT_SIM)
        assert method.threshold == 1

    def test_uses_levenshtein_score_function(self):
        method = get_scoring_method(ScoringMethodNames.EDIT_SIM)
        assert is_close(method.scoring_fn('axb', 'ayb'), 2 / 3)

    def test_preprocessing_strips_punctuation_and_whitespace(self):
        method = get_scoring_method(ScoringMethodNames.EDIT_SIM)
        assert method.preprocessing_fn('hello, world!') == 'helloworld'
