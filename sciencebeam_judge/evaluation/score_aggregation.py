from __future__ import division

import logging

from itertools import groupby
from typing import Optional, Sequence

from sciencebeam_utils.utils.collection import extend_dict, iter_flatten, flatten

from sciencebeam_judge.evaluation.metrics import (
    f1_for_precision_recall,
    jaccard_index,
    precision_for_tp_fp,
    recall_for_tp_fn
)

from .math import safe_mean

from .document_scoring import (
    document_score_key_fn,
    document_score_key_to_props,
    DocumentScoringProps
)


LOGGER = logging.getLogger(__name__)


class CombinedScoresProps:
    MATCH_SCORES = 'match_scores'


class SummaryScoresProps:
    SUMMARY_SCORES = 'summary_scores'


def force_list(x):
    return x if isinstance(x, list) else [x]


def sum_scores_with_true_negative(scores, total_fields=None):
    tp = sum([s['true_positive'] for s in scores])
    fp = sum([s['false_positive'] for s in scores])
    fn = sum([s['false_negative'] for s in scores])
    d = {
        'true_positive': tp,
        'false_positive': fp,
        'false_negative': fn
    }
    if total_fields is not None:
        tn = total_fields - tp - fp - fn
        d['true_negative'] = tn
    return d


def summary_score(sum_scores):
    tp = sum_scores['true_positive']
    fp = sum_scores['false_positive']
    fn = sum_scores['false_negative']
    tn = sum_scores['true_negative']
    accuracy = (tp + tn) / (tp + fp + tn + fn) if tp + fp + tn + fn > 0 else 0
    precision = precision_for_tp_fp(tp, fp)
    recall = recall_for_tp_fn(tp, fn)
    f1 = f1_for_precision_recall(precision, recall)
    jaccard = jaccard_index(tp, fn, fp)
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'jaccard': jaccard
    }


def compact_scores(scores, total_fields=None, keys=None):
    if not scores:
        return {}
    if keys is None:
        keys = scores.keys()
    return {
        k: sum_scores_with_true_negative(scores[k], total_fields)
        for k in keys
    }


def combine_scores(list_of_scores, keys=None):
    if not list_of_scores:
        return {}
    combined_scores = dict()
    for scores in list_of_scores:
        for k, v in scores.items():
            if keys is None or k in keys:
                combined_scores.setdefault(k, []).extend(
                    v if isinstance(v, list) else [v]
                )
    return combined_scores


def groupby_document_score_key(document_scores):
    key_fn = document_score_key_fn
    return groupby(
        sorted(document_scores, key=key_fn), key_fn
    )


def combine_and_compact_document_scores(document_scores):
    document_scores = list(document_scores)
    LOGGER.debug('document_scores: %s', document_scores)
    return [
        extend_dict(document_score_key_to_props(document_score_key), {
            DocumentScoringProps.MATCH_SCORE: sum_scores_with_true_negative(
                [
                    x[DocumentScoringProps.MATCH_SCORE]
                    for x in grouped_document_scores
                ]
            )
        })
        for document_score_key, grouped_document_scores in groupby_document_score_key(
            document_scores
        )
    ]


def combine_and_compact_document_scores_with_count(document_scores_with_count):
    LOGGER.debug('document_scores_with_count: %s', document_scores_with_count)
    return (
        combine_and_compact_document_scores(iter_flatten(
            list_of_scores for list_of_scores, _ in document_scores_with_count
        )),
        sum(
            count for _, count in document_scores_with_count
        )
    )


def summarise_binary_results(
    scores: dict,
    keys: Sequence[str],
    count: Optional[int] = None
):
    scores = {k: force_list(x) for k, x in scores.items()}
    LOGGER.debug(
        'summarise_binary_results, scores.keys=%s, keys=%s', scores.keys(), keys
    )
    keys = [k for k in keys if k in scores]
    score_fields = ['accuracy', 'precision', 'recall', 'f1', 'jaccard']
    # if not isinstance(scores, list):
    #   scores = [scores]
    total_fields = sum([
        s['true_positive'] + s['false_negative'] + 2 * s['false_positive']
        for s in flatten([scores[k] for k in keys])
    ])
    sum_scores_map = {
        k: sum_scores_with_true_negative(
            scores[k], total_fields
        )
        for k in keys
    }
    summary_score_map = {k: summary_score(sum_scores_map[k]) for k in keys}
    total_sums = {
        k: sum(sum_scores[k] for sum_scores in sum_scores_map.values())
        for k in ['true_positive', 'false_negative', 'false_positive', 'true_negative']
    }
    micro_avg_scores = summary_score(total_sums)
    macro_avg_scores = {
        f: safe_mean([summary_score_map[k][f] for k in keys])
        for f in score_fields
    }
    return {
        'by-field': {
            k: {
                'total': sum_scores_map[k],
                'scores': summary_score_map.get(k)
            }
            for k in keys
        },
        'total': total_sums,
        'micro': micro_avg_scores,
        'macro': macro_avg_scores,
        'count': count
    }


def grouped_document_scores_to_scores_by_field_name(grouped_document_scores):
    return {
        document_score[DocumentScoringProps.FIELD_NAME]: (
            document_score[DocumentScoringProps.MATCH_SCORE]
        )
        for document_score in grouped_document_scores
    }


def summarise_combined_document_scores(document_scores, keys, count=None):
    def key_fn(document_score):
        return (
            document_score[DocumentScoringProps.SCORING_TYPE],
            document_score[DocumentScoringProps.SCORING_METHOD]
        )

    def key_to_props(key):
        return {
            DocumentScoringProps.SCORING_TYPE: key[0],
            DocumentScoringProps.SCORING_METHOD: key[1]
        }
    return [
        extend_dict(key_to_props(key), {
            SummaryScoresProps.SUMMARY_SCORES: summarise_binary_results(
                grouped_document_scores_to_scores_by_field_name(
                    grouped_document_scores
                ),
                keys=keys,
                count=count
            )
        })
        for key, grouped_document_scores in groupby(sorted(document_scores, key=key_fn), key_fn)
    ]


def summarise_combined_document_scores_with_count(scores_with_count, keys):
    return summarise_combined_document_scores(
        scores_with_count[0],
        keys,
        count=scores_with_count[1]
    )
