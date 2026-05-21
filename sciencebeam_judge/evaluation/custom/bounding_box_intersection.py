import logging
from typing import List, Optional, Sequence

from sciencebeam_judge.utils.distance_matching import type_checked_distance_function
from sciencebeam_judge.utils.bounding_box import (
    BoundingBox,
    PageBoundingBox,
    PageBoundingBoxList,
    get_merged_page_bounding_box_lists
)
from sciencebeam_judge.evaluation.metrics import (
    f1_for_precision_recall,
    precision_for_tp_fp,
    recall_for_tp_fn
)
from sciencebeam_judge.evaluation.match_scoring import MatchScore
from sciencebeam_judge.evaluation.scoring_methods.scoring_methods import ScoringMethod
from sciencebeam_judge.evaluation.scoring_types.scoring_types import (
    ScoringTypeNames,
    resolve_scoring_type
)
from sciencebeam_judge.evaluation.custom import CustomEvaluation


LOGGER = logging.getLogger(__name__)


DEFAULT_BOUNDING_BOX_SCORING_TYPE_NAME = ScoringTypeNames.PARIAL_ULIST

DEFAULT_BOUNDING_BOX_RESOLUTION = 1000


def parse_page_bounding_box(text: str) -> PageBoundingBox:
    assert text
    fragments = text.split(',')
    assert len(fragments) == 5
    return PageBoundingBox(
        page_number=int(fragments[0]),
        bounding_box=BoundingBox(
            x=float(fragments[1]),
            y=float(fragments[2]),
            width=float(fragments[3]),
            height=float(fragments[4])
        )
    )


def parse_page_bounding_box_list(text: str) -> PageBoundingBoxList:
    if not text:
        return PageBoundingBoxList([])
    fragments = text.split(';')
    return PageBoundingBoxList([
        parse_page_bounding_box(fragment)
        for fragment in fragments
    ])


def parse_page_bounding_box_list_of_list(
    text_list: Sequence[str]
) -> Sequence[PageBoundingBoxList]:
    return [
        parse_page_bounding_box_list(text)
        for text in text_list
    ]


def format_bounding_box(bounding_box: BoundingBox) -> str:
    return f'{bounding_box.x},{bounding_box.y},{bounding_box.width},{bounding_box.height}'


def format_page_bounding_box(page_bounding_box: PageBoundingBox) -> str:
    bounding_box_text = format_bounding_box(page_bounding_box.bounding_box)
    return f'{page_bounding_box.page_number},{bounding_box_text}'


def format_page_bounding_box_list(page_bounding_box_list: PageBoundingBoxList) -> str:
    return ';'.join((
        format_page_bounding_box(page_bounding_box)
        for page_bounding_box in page_bounding_box_list.non_empty_page_bounding_box_list
    ))


def get_page_bounding_box_list_area_match_score(
    page_bounding_box_list_1: PageBoundingBoxList,
    page_bounding_box_list_2: PageBoundingBoxList
) -> float:
    max_area = max(page_bounding_box_list_1.area, page_bounding_box_list_2.area)
    if not max_area:
        intersection_ratio = 1.0
        LOGGER.debug(
            'max_area=%f, intersection_ratio=%f',
            max_area, intersection_ratio
        )
        return intersection_ratio
    intersection_page_bounding_box_list = page_bounding_box_list_1.intersection(
        page_bounding_box_list_2
    )
    intersection_area = intersection_page_bounding_box_list.area
    intersection_ratio = intersection_area / max_area
    LOGGER.debug(
        'intersection_area=%f, max_area=%f, intersection_ratio=%f',
        intersection_area, max_area, intersection_ratio
    )
    return intersection_ratio


def get_formatted_page_bounding_box_list_area_match_score(
    formatted_page_bounding_box_list_1: str,
    formatted_page_bounding_box_list_2: str
) -> float:
    return get_page_bounding_box_list_area_match_score(
        parse_page_bounding_box_list(formatted_page_bounding_box_list_1),
        parse_page_bounding_box_list(formatted_page_bounding_box_list_2)
    )


def get_page_bounding_box_list_area_match_score_obj(
    expected_page_bounding_box_list: PageBoundingBoxList,
    actual_page_bounding_box_list: PageBoundingBoxList,
    resolution: float = DEFAULT_BOUNDING_BOX_RESOLUTION,
    include_values: bool = True
) -> MatchScore:
    expected_page_bounding_box_list = expected_page_bounding_box_list.scale_by(
        resolution, resolution
    ).round()
    actual_page_bounding_box_list = actual_page_bounding_box_list.scale_by(
        resolution, resolution
    ).round()
    intersection_page_bounding_box_list = expected_page_bounding_box_list.intersection(
        actual_page_bounding_box_list
    )
    intersection_area = intersection_page_bounding_box_list.area
    expected_area = expected_page_bounding_box_list.area
    actual_area = actual_page_bounding_box_list.area
    true_positive = round(intersection_area)
    false_positive = round(actual_area - intersection_area)
    false_negative = round(expected_area - intersection_area)
    precision = precision_for_tp_fp(true_positive, false_positive)
    recall = recall_for_tp_fn(true_positive, false_negative)
    f1 = f1_for_precision_recall(precision, recall)
    return MatchScore(
        f1,
        expected_something=bool(expected_page_bounding_box_list),
        actual_something=bool(actual_page_bounding_box_list),
        true_positive=true_positive,
        false_positive=false_positive,
        false_negative=false_negative,
        expected=(
            format_page_bounding_box_list(expected_page_bounding_box_list)
            if include_values
            else None
        ),
        actual=(
            format_page_bounding_box_list(actual_page_bounding_box_list)
            if include_values
            else None
        )
    )


def get_page_bounding_box_list_of_list_area_match_score_obj(
    expected_page_bounding_box_list_of_list: Sequence[PageBoundingBoxList],
    actual_page_bounding_box_list_of_list: Sequence[PageBoundingBoxList],
    **kwargs
) -> MatchScore:
    return get_page_bounding_box_list_area_match_score_obj(
        expected_page_bounding_box_list=get_merged_page_bounding_box_lists(
            expected_page_bounding_box_list_of_list
        ),
        actual_page_bounding_box_list=get_merged_page_bounding_box_lists(
            actual_page_bounding_box_list_of_list
        ),
        **kwargs
    )


def get_formatted_page_bounding_box_list_of_list_area_match_score_obj(
    expected_formatted_page_bounding_box_list_of_list: Sequence[str],
    actual_formatted_page_bounding_box_list_of_list: Sequence[str],
    **kwargs
) -> MatchScore:
    return get_page_bounding_box_list_of_list_area_match_score_obj(
        parse_page_bounding_box_list_of_list(
            expected_formatted_page_bounding_box_list_of_list
        ),
        parse_page_bounding_box_list_of_list(
            actual_formatted_page_bounding_box_list_of_list
        ),
        **kwargs
    )


BOUNDING_BOX_INTERSECTION_SCORING_METHOD = ScoringMethod(
    'bounding_box_intersection',
    type_checked_distance_function(
        get_formatted_page_bounding_box_list_area_match_score,
        str
    ),
    threshold=0.8
)


class BoundingBoxIntersectionEvaluation(CustomEvaluation):
    """
    Calculate an evaluation metric similar to text based metrics.
    Similarity Score = Intersection_area / max(Ground_truth_area, Detected_area)

    Two bounding boxes are then treated as a match, if, and only if,
    the similarity score is above or equal to a threshold (0.8).
    """
    def __init__(self, config: Optional[dict] = None):
        super().__init__()
        self.scoring_type_name = (  # pylint: disable=consider-using-ternary
            (config and config.get('scoring_type'))
            or DEFAULT_BOUNDING_BOX_SCORING_TYPE_NAME
        )
        self.scoring_type = resolve_scoring_type(self.scoring_type_name)

    def score(
        self,
        expected: List[str],
        actual: List[str],
        include_values: bool = True
    ) -> MatchScore:
        score_dict = self.scoring_type.score(
            expected,
            actual,
            include_values=include_values,
            measures=[BOUNDING_BOX_INTERSECTION_SCORING_METHOD]
        )
        LOGGER.debug('score_dict: %r', score_dict)
        return MatchScore.from_dict(score_dict[BOUNDING_BOX_INTERSECTION_SCORING_METHOD.name])


class BoundingBoxIntersectionAreaEvaluation(CustomEvaluation):
    """
    Calculate an evaluation metric similar to the one proposed by DocBank:
    https://github.com/doc-analysis/DocBank

    Precision = Area_of_Ground_truth_tokens_in_Detected_tokens / Area_of_all_Detected_tokens
    Recall = Area_of_Ground_truth_tokens_in_Detected_tokens / Area_of_all_Ground_truth_tokens
    F1 = 2 * Precision * Recall / (Precision + Recall)

    Using the common definitions of Precision and Recall:
    Precision = tp / (tp + fp)
    Recall = tp / (tp + fn)

    We can define it in terms of tp, fp an fn:
    tp: Area_of_Ground_truth_tokens in Area_of_Detected_tokens
    fp: Area_of_Detected_tokens not in Area_of_Ground_truth_tokens
    fn: Area_of_Ground_truth_tokens not in Area_of_Detected_tokens

    We will round the area to the nearest integer value.
    To have a higher resolution, the bounding box coordinates may be multiplied by a fixed value
    (e.g. 1000).

    Tokens here will be the figure for example, with the bounding box defining the area.
    """
    def __init__(self, config: Optional[dict] = None):
        super().__init__()
        self.resolution = float(  # pylint: disable=consider-using-ternary
            (config and config.get('resolution')) or DEFAULT_BOUNDING_BOX_RESOLUTION
        )

    def score(
        self,
        expected: List[str],
        actual: List[str],
        include_values: bool = True
    ) -> MatchScore:
        match_score = get_formatted_page_bounding_box_list_of_list_area_match_score_obj(
            expected_formatted_page_bounding_box_list_of_list=expected,
            actual_formatted_page_bounding_box_list_of_list=actual,
            include_values=include_values,
            resolution=self.resolution
        )
        LOGGER.debug('match_score: %r (resolution: %r)', match_score, self.resolution)
        return match_score
