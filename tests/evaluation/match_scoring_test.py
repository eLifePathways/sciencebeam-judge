from sciencebeam_judge.evaluation.match_scoring import (
    get_match_score_obj_for_score,
    get_match_score_obj_for_continuous_score,
    ContinuousMatchScoringProps,
    MatchScoringProps
)


TEXT_1 = 'abc'
TEXT_2 = '123'


class TestGetMatchScoreObjForScore:
    def test_should_count_as_tp_for_match(self):
        match_score = get_match_score_obj_for_score(TEXT_1, TEXT_1, 1.0)
        assert match_score[MatchScoringProps.TRUE_POSITIVE] == 1
        assert match_score[MatchScoringProps.FALSE_POSITIVE] == 0
        assert match_score[MatchScoringProps.FALSE_NEGATIVE] == 0
        assert match_score[MatchScoringProps.TRUE_NEGATIVE] == 0

    def test_should_count_as_fp_for_mismatch(self):
        match_score = get_match_score_obj_for_score(TEXT_1, TEXT_2, 0.0)
        assert match_score[MatchScoringProps.TRUE_POSITIVE] == 0
        assert match_score[MatchScoringProps.FALSE_POSITIVE] == 1
        assert match_score[MatchScoringProps.FALSE_NEGATIVE] == 0
        assert match_score[MatchScoringProps.TRUE_NEGATIVE] == 0

    def test_should_count_as_fp_for_no_expected_but_actual_value(self):
        match_score = get_match_score_obj_for_score('', TEXT_2, 0.0)
        assert match_score[MatchScoringProps.TRUE_POSITIVE] == 0
        assert match_score[MatchScoringProps.FALSE_POSITIVE] == 1
        assert match_score[MatchScoringProps.FALSE_NEGATIVE] == 0
        assert match_score[MatchScoringProps.TRUE_NEGATIVE] == 0

    def test_should_count_as_fn_for_expected_but_no_actual_value(self):
        match_score = get_match_score_obj_for_score(TEXT_1, '', 0.0)
        assert match_score[MatchScoringProps.TRUE_POSITIVE] == 0
        assert match_score[MatchScoringProps.FALSE_POSITIVE] == 0
        assert match_score[MatchScoringProps.FALSE_NEGATIVE] == 1
        assert match_score[MatchScoringProps.TRUE_NEGATIVE] == 0

    def test_should_count_as_tn_for_no_expected_and_no_actual_value(self):
        match_score = get_match_score_obj_for_score('', '', 1.0)
        assert match_score[MatchScoringProps.TRUE_POSITIVE] == 0
        assert match_score[MatchScoringProps.FALSE_POSITIVE] == 0
        assert match_score[MatchScoringProps.FALSE_NEGATIVE] == 0
        assert match_score[MatchScoringProps.TRUE_NEGATIVE] == 1

    def test_should_count_as_tn_for_no_expected_and_no_actual_value_with_incorrect_zero_score(self):
        match_score = get_match_score_obj_for_score('', '', 0.0)
        assert match_score[MatchScoringProps.TRUE_POSITIVE] == 0
        assert match_score[MatchScoringProps.FALSE_POSITIVE] == 0
        assert match_score[MatchScoringProps.FALSE_NEGATIVE] == 0
        assert match_score[MatchScoringProps.TRUE_NEGATIVE] == 1


class TestGetMatchScoreObjForContinuousScore:
    def test_case_d_both_present_contributes_sim_to_both_counts(self):
        score = get_match_score_obj_for_continuous_score('abc', 'abc', 1.0)
        assert score[ContinuousMatchScoringProps.SIM_SUM] == 1.0
        assert score[ContinuousMatchScoringProps.EXPECTED_COUNT] == 1
        assert score[ContinuousMatchScoringProps.PREDICTED_COUNT] == 1

    def test_case_d_partial_similarity(self):
        score = get_match_score_obj_for_continuous_score('abc', 'axc', 0.667)
        assert score[ContinuousMatchScoringProps.SIM_SUM] == 0.667
        assert score[ContinuousMatchScoringProps.EXPECTED_COUNT] == 1
        assert score[ContinuousMatchScoringProps.PREDICTED_COUNT] == 1

    def test_case_a_both_absent_is_neutral(self):
        score = get_match_score_obj_for_continuous_score('', '', 0.0)
        assert score[ContinuousMatchScoringProps.SIM_SUM] == 0.0
        assert score[ContinuousMatchScoringProps.EXPECTED_COUNT] == 0
        assert score[ContinuousMatchScoringProps.PREDICTED_COUNT] == 0

    def test_case_b_gold_present_predicted_absent_is_recall_penalty(self):
        score = get_match_score_obj_for_continuous_score('abc', '', 0.0)
        assert score[ContinuousMatchScoringProps.SIM_SUM] == 0.0
        assert score[ContinuousMatchScoringProps.EXPECTED_COUNT] == 1
        assert score[ContinuousMatchScoringProps.PREDICTED_COUNT] == 0

    def test_case_c_gold_absent_predicted_present_is_precision_penalty(self):
        score = get_match_score_obj_for_continuous_score('', 'abc', 0.0)
        assert score[ContinuousMatchScoringProps.SIM_SUM] == 0.0
        assert score[ContinuousMatchScoringProps.EXPECTED_COUNT] == 0
        assert score[ContinuousMatchScoringProps.PREDICTED_COUNT] == 1

    def test_include_values_stores_expected_and_actual(self):
        score = get_match_score_obj_for_continuous_score('abc', 'axc', 0.667, include_values=True)
        assert score[MatchScoringProps.EXPECTED] == 'abc'
        assert score[MatchScoringProps.ACTUAL] == 'axc'

    def test_without_include_values_does_not_store_expected_and_actual(self):
        score = get_match_score_obj_for_continuous_score('abc', 'axc', 0.667)
        assert MatchScoringProps.EXPECTED not in score
        assert MatchScoringProps.ACTUAL not in score
