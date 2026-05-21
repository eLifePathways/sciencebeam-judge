from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from itertools import groupby
import logging
from typing import Any, Dict, Sequence

from sciencebeam_utils.utils.collection import flatten

from .evaluation.scoring_methods.scoring_methods import ScoringMethodNames
from .evaluation.scoring_types.scoring_types import ScoringTypeNames
from .evaluation.document_scoring import DocumentScoringProps
from .evaluation.score_aggregation import SummaryScoresProps


HEADER_BY_SCORE_MEASURE = {
    ScoringMethodNames.EXACT: (
        "======= Strict Matching ======= (exact matches)"
    ),
    ScoringMethodNames.SOFT: (
        "======== Soft Matching ========"
        " (ignoring punctuation, case and space characters mismatches)"
    ),
    ScoringMethodNames.LEVENSHTEIN: (
        "==== Levenshtein Matching ===== (Minimum Levenshtein distance at 0.8)"
    ),
    ScoringMethodNames.RATCLIFF_OBERSHELP: (
        "= Ratcliff/Obershelp Matching = (Minimum Ratcliff/Obershelp similarity at 0.95)"
    )
}


def get_logger():
    return logging.getLogger(__name__)


def format_summarised_results(summarised_results, keys):
    score_fields = ['accuracy', 'precision', 'recall', 'f1', 'jaccard']
    summary_scores = [
        (k, summarised_results['by-field'][k]['scores'])
        for k in keys
    ]
    micro_avg_scores = summarised_results['micro']
    macro_avg_scores = summarised_results['macro']
    rows = [
        ['label'] + score_fields,
        []
    ] + [
        [k] + [score[f] * 100 for f in score_fields]
        for k, score in summary_scores
    ] + [
        []
    ] + [
        ['all fields'] +
        [micro_avg_scores[f] * 100 for f in score_fields] +
        ['(micro average)']
    ] + [
        [] +
        [macro_avg_scores[f] * 100 for f in score_fields] +
        ['(macro average)']
    ]
    rows = [[
        '{:.2f}'.format(x)
        if not isinstance(x, str)
        else x
        for x in row
    ] for row in rows]
    column_widths = [20, 10, 10, 10, 10, 10, 20]
    rows = [[
        x.rjust(c, ' ')
        for x, c in zip(row, column_widths)
    ] for row in rows]
    return '\n'.join([' '.join(row) for row in rows])


def format_summary_by_scoring_method(
    scores_by_scoring_method: Dict[str, Dict[str, Any]],
    keys: Sequence[str]
) -> str:
    available_keys = set(flatten([
        scores_for_scoring_method['by-field'].keys()
        for scores_for_scoring_method in scores_by_scoring_method.values()
    ]))
    print('available_keys:', available_keys, ', keys:', keys)
    keys = [k for k in keys if k in available_keys]
    score_measures = [
        ScoringMethodNames.EXACT, ScoringMethodNames.SOFT,
        ScoringMethodNames.LEVENSHTEIN, ScoringMethodNames.RATCLIFF_OBERSHELP
    ]
    if not scores_by_scoring_method:
        return ''
    if not (set(score_measures) & set(scores_by_scoring_method.keys())):
        raise ValueError(
            'invalid scores_by_scoring_method, expected at least one of %s, but had: %s' %
            (score_measures, scores_by_scoring_method.keys())
        )
    score_outputs = []
    for measure in score_measures:
        if measure in scores_by_scoring_method:
            score_outputs.append(
                """
  {header}

  ===== Field-level results =====

  {results}
                """.format(
                    header=HEADER_BY_SCORE_MEASURE[measure],
                    results=format_summarised_results(
                        scores_by_scoring_method[measure],
                        keys
                    )
                ).rstrip())
    return "\n\n".join(score_outputs)


def get_scoring_method_and_type(summary_scores):
    return (
        summary_scores[DocumentScoringProps.SCORING_METHOD],
        summary_scores[DocumentScoringProps.SCORING_TYPE]
    )


def summarised_document_scores_to_scores_by_scoring_method(summarised_document_scores):
    d = {}
    grouped = groupby(
        sorted(summarised_document_scores, key=get_scoring_method_and_type),
        get_scoring_method_and_type
    )
    for scoring_method_and_type, grouped_summary_scores in grouped:
        scoring_method, scoring_type = scoring_method_and_type
        grouped_summary_scores = list(grouped_summary_scores)
        if scoring_type == ScoringTypeNames.STRING:
            d[scoring_method] = grouped_summary_scores[0][SummaryScoresProps.SUMMARY_SCORES]
        else:
            get_logger().info(
                'only considering results with single scoring type,'
                ' found %d scores for %s (ignoring)',
                len(grouped_summary_scores), scoring_method
            )
    return d


def format_summarised_document_scores_as_grobid_report(summarised_document_scores, keys):
    return format_summary_by_scoring_method(
        summarised_document_scores_to_scores_by_scoring_method(
            summarised_document_scores
        ),
        keys
    )
