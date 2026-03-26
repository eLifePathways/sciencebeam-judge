import argparse
import logging
import os
import random
import pstats
import cProfile
from collections import OrderedDict
from itertools import islice
from timeit import timeit
from typing import List, Tuple

import pyprof2calltree

import lorem

from sciencebeam_judge.parsing.xml import parse_xml, parse_xml_mapping
from sciencebeam_judge.parsing.xpath.xpath_functions import register_functions

from sciencebeam_judge.evaluation.scoring_methods.scoring_methods import levenshtein_score

from sciencebeam_judge.utils.distance_matching import (
    DistanceMeasure,
    Value_Types,
    get_length_based_upper_bound_score,
    get_character_count_based_upper_bound_score,
    get_distance_matches,
    type_checked_distance_function
)


LOGGER = logging.getLogger(__name__)


LEVENSHTEIN_SCORE_DISTANCE_FUNCTION = type_checked_distance_function(
    levenshtein_score,
    Value_Types
)


DISTANCE_MEASURE_WITHOUT_APPROXIMATE = DistanceMeasure(
    LEVENSHTEIN_SCORE_DISTANCE_FUNCTION
)

DISTANCE_MEASURE_WITH_LENGTH_ONLY_APPROXIMATE = DistanceMeasure(
    LEVENSHTEIN_SCORE_DISTANCE_FUNCTION,
    [
        get_length_based_upper_bound_score
    ]
)

DISTANCE_MEASURE_WITH_APPROXIMATE = DistanceMeasure(
    LEVENSHTEIN_SCORE_DISTANCE_FUNCTION,
    [
        get_length_based_upper_bound_score,
        get_character_count_based_upper_bound_score
    ]
)


NAMED_DISTANCE_MEASURES = OrderedDict([
    ('distance_measure_without_approximate', DISTANCE_MEASURE_WITHOUT_APPROXIMATE),
    ('distance_measure_with_length_approximate', DISTANCE_MEASURE_WITH_LENGTH_ONLY_APPROXIMATE),
    ('distance_measure_with_approximate', DISTANCE_MEASURE_WITH_APPROXIMATE)
])


EXAMPLE_DATA_EXPECTED_XML = (
    'example-data/pmc-sample-1943-cc-by-subset'
    '/Acta_Anaesthesiol_Scand_2011_Jan_55(1)_39-45/aas0055-0039.nxml'
)

EXAMPLE_DATA_ACTUAL_XML = (
    'example-data/pmc-sample-1943-cc-by-subset-results'
    '/grobid-tei/Acta_Anaesthesiol_Scand_2011_Jan_55(1)_39-45/aas0055-0039.xml'
)


class DistanceMatchesPerfTester:
    def __init__(
        self,
        name: str,
        distance_measure: DistanceMeasure,
        expected_list: List[str],
        actual_list: List[str]
    ):
        self.name = name
        self.distance_measure = distance_measure
        self.expected_list = expected_list
        self.actual_list = actual_list

    def run_once(self):
        return get_distance_matches(
            self.expected_list,
            self.actual_list,
            self.distance_measure
        )

    def run(self, number: int = 100):
        LOGGER.info('testing: %s', self.name)
        LOGGER.info('distance_measure: %s', self.distance_measure)
        match_results = self.run_once()
        mean_score = sum([m.score for m in match_results]) / max(1, len(match_results))
        LOGGER.info('mean_score: %s', mean_score)
        result = timeit('self.run_once()', globals={'self': self}, number=number)
        LOGGER.info('result: total=%s, mean=%s', result, result / number)
        return result

    def run_and_profile(self, *args, **kwargs) -> cProfile.Profile:
        profile = cProfile.Profile()
        profile.runctx(
            'self.run(*args, **kwargs)',
            globals={},
            locals={'self': self, 'args': args, 'kwargs': kwargs}
        )
        return profile


def modify_text(
    text: str,
    insertion_prob: float,
    deletion_prob: float,
    relative_max_start: float,
    relative_max_end: float
) -> str:
    result = []
    start = round(random.uniform(0.0, relative_max_start) * len(text))
    end = round(random.uniform(1.0 - relative_max_end, 1.0) * len(text))
    text = text[start:end]
    for c in text:
        if random.uniform(0.0, 1.0) < insertion_prob:
            result.append(random.choice(text))
        if random.uniform(0.0, 1.0) < deletion_prob:
            continue
        result.append(c)
    return ''.join(result)


def get_generated_expected_actual_list(
    paragraph_count: int = 20,
    actual_extra_paragraph_count: int = 3,
    actual_missing_paragraph_count: int = 3,
    count_arg: int = 1,
    sentence_word_range: Tuple[int, int] = (5, 20),
    sentence_range: Tuple[int, int] = (5, 20),
    insertion_prob: float = 0.2,
    deletion_prob: float = 0.2,
    relative_max_start: float = 0.1,
    relative_max_end: float = 0.1
):
    paragraphs = list(islice(lorem.paragraph(
        count_arg,
        word_range=sentence_word_range,
        sentence_range=sentence_range
    ), paragraph_count))
    LOGGER.info('paragraphs[0]: %s', paragraphs[0])
    LOGGER.info('paragraphs count: %d', len(paragraphs))
    expected_list = paragraphs
    actual_list = (
        paragraphs.copy()[actual_missing_paragraph_count:]
        + list(islice(lorem.paragraph(
            count_arg,
            word_range=sentence_word_range,
            sentence_range=sentence_range
        ), actual_extra_paragraph_count))
    )
    random.shuffle(actual_list)
    actual_list = [
        modify_text(
            text,
            insertion_prob=insertion_prob,
            deletion_prob=deletion_prob,
            relative_max_start=relative_max_start,
            relative_max_end=relative_max_end
        )
        for text in actual_list
    ]
    LOGGER.info('actual_list[0]: %s', actual_list[0])
    return expected_list, actual_list


def run_profiler(
    expected_list: List[str],
    actual_list: List[str],
    iteration_count: int
):
    for name, distance_measure in NAMED_DISTANCE_MEASURES.items():
        profile_filename = os.path.join(
            '.temp',
            f'distance_matching_{name}.profile'
        )
        calltree_filename = os.path.splitext(profile_filename)[0] + '.calltree'
        LOGGER.info('profile_filename: %s (%s)', profile_filename, calltree_filename)
        profile = DistanceMatchesPerfTester(
            name=name,
            distance_measure=distance_measure,
            expected_list=expected_list,
            actual_list=actual_list
        ).run_and_profile(iteration_count)
        profile.dump_stats(profile_filename)
        pyprof2calltree.convert(profile_filename, calltree_filename)
        pstats.Stats(profile).sort_stats('tottime').print_stats(5)


def generate_text_and_profile(**kwargs):
    expected_list, actual_list = get_generated_expected_actual_list()
    run_profiler(expected_list=expected_list, actual_list=actual_list, **kwargs)


def load_example_data_and_profile(
    expected_xml_path: str,
    actual_xml_path: str,
    **kwargs
):
    xml_mapping = get_default_xml_mapping()
    expected_data = parse_xml(
        expected_xml_path,
        xml_mapping=xml_mapping,
        fields=['all_section_paragraphs']
    )
    expected_list = expected_data['all_section_paragraphs']
    LOGGER.info('expected_list[0]: %s', expected_list[0])
    LOGGER.info('len(expected_list): %s', len(expected_list))

    actual_data = parse_xml(
        actual_xml_path,
        xml_mapping=xml_mapping,
        fields=['all_section_paragraphs']
    )
    actual_list = actual_data['all_section_paragraphs']
    LOGGER.info('actual_list[0]: %s', actual_list[0])
    LOGGER.info('len(actual_list): %s', len(actual_list))
    run_profiler(expected_list=expected_list, actual_list=actual_list, **kwargs)


def get_default_xml_mapping():
    register_functions()
    return parse_xml_mapping('./xml-mapping.conf')


def main(argv: List[str] = None):
    parser = argparse.ArgumentParser('Distance Matching Profile')
    parser.add_argument(
        '--expected-xml',
        default=EXAMPLE_DATA_EXPECTED_XML
    )
    parser.add_argument(
        '--actual-xml',
        default=EXAMPLE_DATA_ACTUAL_XML
    )
    parser.add_argument(
        '--iterations',
        type=int,
        default=1
    )
    args = parser.parse_args(argv)
    LOGGER.info('args: %s', args)
    # generate_text_and_profile(iteration_count=args.iterations)
    load_example_data_and_profile(
        args.expected_xml,
        args.actual_xml,
        iteration_count=args.iterations
    )


if __name__ == '__main__':
    logging.basicConfig(level='INFO')
    main()
