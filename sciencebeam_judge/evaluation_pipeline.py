from __future__ import absolute_import

import argparse
import os
import logging
from io import BytesIO
from functools import partial
from typing import Dict, List, Optional

import apache_beam as beam
from apache_beam.io.textio import WriteToText
from apache_beam.options.pipeline_options import (
    PipelineOptions,
    SetupOptions,
    DirectOptions,
    WorkerOptions
)

from sciencebeam_utils.utils.collection import (
    extend_dict
)

from sciencebeam_utils.beam_utils.utils import (
    TransformAndLog,
    TransformAndCount,
    MapOrLog,
    PreventFusion
)

from sciencebeam_utils.beam_utils.csv import (
    WriteDictCsv
)

from sciencebeam_utils.beam_utils.io import (
    read_all_from_path
)

from sciencebeam_utils.beam_utils.main import (
    add_cloud_args,
    process_cloud_args
)

from sciencebeam_utils.utils.file_list import (
    load_file_list
)

from sciencebeam_judge.evaluation_utils import (
    get_plus_minus_comma_separated_str_to_list_fn
)

from sciencebeam_judge.parsing.xml import (
    parse_xml,
    parse_xml_mapping
)

from sciencebeam_judge.evaluation_config import (
    DEFAULT_EVALUATION_YAML_FILENAME,
    EvaluationConfig,
    parse_evaluation_config,
    parse_evaluation_yaml_config,
    get_evaluation_config_object,
    parse_scoring_type_overrides,
    get_scoring_types_by_field_map_from_config
)

from sciencebeam_judge.grobid_evaluate import (
    format_summarised_document_scores_as_grobid_report
)

from .evaluation.match_scoring import (
    MatchScoringProps
)

from .evaluation.scoring_methods.scoring_methods import (
    ScoringMethodNames,
    ALL_SCORING_METHOD_NAMES
)

from .evaluation.score_aggregation import (
    combine_and_compact_document_scores_with_count,
    summarise_combined_document_scores_with_count,
    SummaryScoresProps
)

from .evaluation.document_scoring import (
    iter_score_document_fields_using_config,
    DocumentScoringProps
)

from .parsing.xpath.xpath_functions import register_functions

from .default_field_names import DEFAULT_EXTRACTION_FIELDS
from .resources import DEFAULT_XML_MAPPING_PATH, DEFAULT_EVALUATION_CONFIG_PATH


DEFAULT_SCORE_MEASURES = [
    ScoringMethodNames.EXACT,
    ScoringMethodNames.LEVENSHTEIN
]


LOGGER = logging.getLogger(__name__)


def get_logger():
    return logging.getLogger(__name__)


class MetricCounters:
    FILE_PAIRS = 'file_pairs'
    READ_ERROR = 'read_error'
    EVALUATION_ERROR = 'evaluation_error'


class DataProps:
    TARGET_FILE_URL = 'target_file'
    PREDICTION_FILE_URL = 'prediction_file'
    TARGET_CONTENT = 'target_content'
    PREDICTION_CONTENT = 'prediction_content'
    EVALUTATION_RESULTS = 'evaluation_results'


def ReadFilePairs(x):
    get_logger().info(
        'reading: target: %s, prediction: %s',
        x[DataProps.TARGET_FILE_URL], x[DataProps.PREDICTION_FILE_URL]
    )
    return extend_dict(x, {
        DataProps.TARGET_CONTENT: read_all_from_path(x[DataProps.TARGET_FILE_URL]),
        DataProps.PREDICTION_CONTENT: read_all_from_path(x[DataProps.PREDICTION_FILE_URL])
    })


def get_all_source_field_names(
    evaluation_config: EvaluationConfig,
    field_names: Optional[List[str]]
) -> Optional[List[str]]:
    if not field_names:
        LOGGER.debug('get_all_source_field_names: no field names')
        return field_names
    if not evaluation_config.custom or not evaluation_config.custom.fields:
        LOGGER.debug('get_all_source_field_names: no custom evaluation config or fields')
        return field_names
    field_names = field_names.copy()
    for custom_evaluation_field in evaluation_config.custom.fields:
        if custom_evaluation_field.name not in field_names:
            LOGGER.debug(
                'get_all_source_field_names: custom field not selected: %r (selected: %r)',
                custom_evaluation_field.name, field_names
            )
            continue
        source_field_names = (
            custom_evaluation_field.expected.field_names
            + custom_evaluation_field.actual.field_names
        )
        for source_field_name in source_field_names:
            if source_field_name in field_names:
                continue
            field_names.append(source_field_name)
    return field_names


def evaluate_file_pairs(
        target_filename, target_content,
        prediction_filename, prediction_content,
        xml_mapping, field_names,
        evaluation_config: EvaluationConfig,
        **kwargs):

    try:
        get_logger().info(
            'processing: target: %s, prediction: %s', target_filename, prediction_filename
        )
        source_field_names = get_all_source_field_names(
            evaluation_config=evaluation_config,
            field_names=field_names
        )
        # Note: we need to register functions again,
        #   in case Apache Beam is running this on another worker
        register_functions()
        target_xml = parse_xml(
            BytesIO(target_content),
            xml_mapping,
            fields=source_field_names,
            filename=target_filename
        )
        prediction_xml = parse_xml(
            BytesIO(prediction_content),
            xml_mapping,
            fields=source_field_names,
            filename=prediction_filename
        )
        return list(iter_score_document_fields_using_config(
            target_xml, prediction_xml, field_names=field_names, include_values=True,
            evaluation_config=evaluation_config,
            **kwargs
        ))
    except Exception as e:
        get_logger().error(
            'uncaught exception processing file (%s): %s',
            target_filename, e, exc_info=e
        )
        raise e


def EvaluateFilePairs(x, **kwargs):
    return extend_dict(x, {
        DataProps.EVALUTATION_RESULTS: evaluate_file_pairs(
            x[DataProps.TARGET_FILE_URL], x[DataProps.TARGET_CONTENT],
            x[DataProps.PREDICTION_FILE_URL], x[DataProps.PREDICTION_CONTENT],
            **kwargs
        )
    })


class OutputColumns:
    PREDICTION_FILE = 'prediction_file'
    TARGET_FILE = 'target_file'
    FIELD_NAME = 'field_name'
    EVALUATION_METHOD = 'evaluation_method'
    SCORING_TYPE = 'scoring_type'
    TP = 'tp'
    FP = 'fp'
    FN = 'fn'
    TN = 'tn'
    EXPECTED = 'expected'
    ACTUAL = 'actual'
    EXPECTED_CONTEXT = 'expected_context'
    ACTUAL_CONTEXT = 'actual_context'


DEFAULT_OUTPUT_COLUMNS = [
    OutputColumns.PREDICTION_FILE,
    OutputColumns.TARGET_FILE,
    OutputColumns.FIELD_NAME,
    OutputColumns.EVALUATION_METHOD,
    OutputColumns.SCORING_TYPE,
    OutputColumns.TP,
    OutputColumns.FP,
    OutputColumns.FN,
    OutputColumns.TN,
    OutputColumns.EXPECTED,
    OutputColumns.ACTUAL,
    OutputColumns.EXPECTED_CONTEXT,
    OutputColumns.ACTUAL_CONTEXT
]


class SummaryOutputColumns:
    DOCUMENT_COUNT = 'document_count'
    EVALUATION_METHOD = 'evaluation_method'
    SCORING_TYPE = 'scoring_type'
    FIELD_NAME = 'field_name'
    STATS_NAME = 'stats_name'
    TP = 'tp'
    FP = 'fp'
    FN = 'fn'
    TN = 'tn'
    ACCURACY = 'accuracy'
    PRECISION = 'precision'
    RECALL = 'recall'
    F1 = 'f1'


DEFAULT_SUMMARY_OUTPUT_COLUMNS = [
    SummaryOutputColumns.DOCUMENT_COUNT,
    SummaryOutputColumns.EVALUATION_METHOD,
    SummaryOutputColumns.SCORING_TYPE,
    SummaryOutputColumns.FIELD_NAME,
    SummaryOutputColumns.STATS_NAME,
    SummaryOutputColumns.TP,
    SummaryOutputColumns.FP,
    SummaryOutputColumns.FN,
    SummaryOutputColumns.TN,
    SummaryOutputColumns.ACCURACY,
    SummaryOutputColumns.PRECISION,
    SummaryOutputColumns.RECALL,
    SummaryOutputColumns.F1
]


def flatten_evaluation_results(evaluation_results, field_names=None):
    C = OutputColumns
    prediction_file = evaluation_results[DataProps.PREDICTION_FILE_URL]
    target_file = evaluation_results[DataProps.TARGET_FILE_URL]
    results = evaluation_results[DataProps.EVALUTATION_RESULTS]
    flat_result = []
    for document_score in results:
        get_logger().debug('document_score: %s', document_score)
        field_name = document_score[DocumentScoringProps.FIELD_NAME]
        if field_name not in field_names:
            continue
        document_match_score = document_score[DocumentScoringProps.MATCH_SCORE]
        match_scores = document_match_score.get(MatchScoringProps.SUB_SCORES)
        if match_scores is None:
            match_scores = [document_match_score]
        for match_score in match_scores:
            get_logger().debug('match_score: %s', match_score)
            flat_result.append({
                C.PREDICTION_FILE: os.path.basename(prediction_file),
                C.TARGET_FILE: os.path.basename(target_file),
                C.FIELD_NAME: field_name,
                C.EVALUATION_METHOD: document_score[DocumentScoringProps.SCORING_METHOD],
                C.SCORING_TYPE: document_score[DocumentScoringProps.SCORING_TYPE],
                C.TP: match_score[MatchScoringProps.TRUE_POSITIVE],
                C.FP: match_score[MatchScoringProps.FALSE_POSITIVE],
                C.FN: match_score[MatchScoringProps.FALSE_NEGATIVE],
                C.TN: match_score[MatchScoringProps.TRUE_NEGATIVE],
                C.EXPECTED: match_score[MatchScoringProps.EXPECTED],
                C.ACTUAL: match_score[MatchScoringProps.ACTUAL],
                C.EXPECTED_CONTEXT: match_score.get(MatchScoringProps.EXPECTED_CONTEXT),
                C.ACTUAL_CONTEXT: match_score.get(MatchScoringProps.ACTUAL_CONTEXT)
            })
    return flat_result


def FlattenEvaluationResults(field_names):
    return partial(flatten_evaluation_results, field_names=field_names)


def flatten_summary_results(summarised_scores, field_names=None):  # pylint: disable=too-many-locals
    get_logger().debug('summarised_scores: %s', summarised_scores)
    C = SummaryOutputColumns
    flat_result = []
    for summarised_score in summarised_scores:
        scoring_type = summarised_score[DocumentScoringProps.SCORING_TYPE]
        scoring_method = summarised_score[DocumentScoringProps.SCORING_METHOD]
        summary = summarised_score[SummaryScoresProps.SUMMARY_SCORES]
        count = summary['count']
        _field_names = field_names or summary['by-field'].keys()
        for field_name in _field_names:
            field_summary = summary['by-field'].get(field_name)
            if not field_summary:
                continue
            field_totals = field_summary['total']
            field_scores = field_summary['scores']
            flat_result.append({
                C.DOCUMENT_COUNT: count,
                C.EVALUATION_METHOD: scoring_method,
                C.SCORING_TYPE: scoring_type,
                C.FIELD_NAME: field_name,
                C.TP: field_totals['true_positive'],
                C.FP: field_totals['false_positive'],
                C.FN: field_totals['false_negative'],
                C.TN: field_totals['true_negative'],
                C.ACCURACY: field_scores['accuracy'],
                C.PRECISION: field_scores['precision'],
                C.RECALL: field_scores['recall'],
                C.F1: field_scores['f1']
            })
        for stats_name in ['micro', 'macro']:
            stats = summary[stats_name]
            flat_result.append({
                C.DOCUMENT_COUNT: count,
                C.EVALUATION_METHOD: scoring_method,
                C.SCORING_TYPE: scoring_type,
                C.STATS_NAME: stats_name,
                C.ACCURACY: stats['accuracy'],
                C.PRECISION: stats['precision'],
                C.RECALL: stats['recall'],
                C.F1: stats['f1']
            })
    return flat_result


def get_scoring_types_by_field_map(opt: argparse.Namespace) -> Dict[str, List[str]]:
    return {
        **get_scoring_types_by_field_map_from_config(
            parse_evaluation_config(opt.evaluation_config)
        ),
        **opt.scoring_type_overrides
    }


def get_evaluation_config(opt: argparse.Namespace) -> EvaluationConfig:
    return get_evaluation_config_object(
        parse_evaluation_yaml_config(opt.evaluation_yaml_config)
    )


def configure_pipeline(p, opt):  # pylint: disable=too-many-locals
    xml_mapping = parse_xml_mapping(opt.xml_mapping)
    evaluation_config = get_evaluation_config(opt)
    scoring_types_by_field_map = get_scoring_types_by_field_map(opt)
    field_names = opt.fields

    target_file_list = load_file_list(
        opt.target_file_list,
        column=opt.target_file_column,
        limit=opt.limit
    )
    prediction_file_list = load_file_list(
        opt.prediction_file_list,
        column=opt.prediction_file_column,
        limit=opt.limit
    )
    assert target_file_list
    assert len(target_file_list) == len(prediction_file_list)

    file_pairs = [{
        DataProps.TARGET_FILE_URL: target_file_url,
        DataProps.PREDICTION_FILE_URL: prediction_file_url
    } for target_file_url, prediction_file_url in zip(target_file_list, prediction_file_list)]

    get_logger().debug('file_pairs: %s', file_pairs)

    evaluate_file_pairs_fn = partial(
        EvaluateFilePairs,
        xml_mapping=xml_mapping,
        evaluation_config=evaluation_config,
        scoring_types_by_field_map=scoring_types_by_field_map,
        field_names=field_names,
        measures=opt.measures,
        convert_to_lower=opt.convert_to_lower
    )
    evaluate_file_pairs_transform = (
        beam.Map(evaluate_file_pairs_fn) if not opt.skip_errors
        else MapOrLog(evaluate_file_pairs_fn, error_count=MetricCounters.EVALUATION_ERROR)
    )

    p_file_pairs = p | beam.Create(file_pairs)

    if not opt.sequential:
        p_file_pairs |= "PreventFusion" >> PreventFusion()

    evaluation_results = (
        p_file_pairs |
        "ReadFilePairs" >> TransformAndCount(
            MapOrLog(
                ReadFilePairs,
                log_fn=lambda e, v: (
                    get_logger().warning(
                        'caught exception (ignoring item): %s, target: %s, prediction: %s',
                        e, v[DataProps.TARGET_FILE_URL], v[DataProps.PREDICTION_FILE_URL],
                        exc_info=e
                    )
                ),
                error_count=MetricCounters.READ_ERROR
            ),
            MetricCounters.FILE_PAIRS
        ) |
        "EvaluateFilePairs" >> TransformAndLog(
            evaluate_file_pairs_transform,
            log_prefix='eval out: ',
            log_value_fn=lambda x: x['evaluation_results'],
            log_level='debug'
        )
    )

    _ = (
        evaluation_results |
        "FlattenEvaluationResults" >> beam.FlatMap(
            FlattenEvaluationResults(field_names=field_names)
        ) |
        "WriteEvaluationToCsv" >> WriteDictCsv(
            os.path.join(opt.output_path, 'results'),
            file_name_suffix='.csv',
            columns=DEFAULT_OUTPUT_COLUMNS
        )
    )

    summary = (
        evaluation_results |
        "ExtractEvaluationResults" >> beam.Map(lambda x: x[DataProps.EVALUTATION_RESULTS]) |
        "PairWithOne" >> beam.Map(lambda x: (x, 1)) |
        "CombineResults" >> TransformAndLog(
            beam.CombineGlobally(
                combine_and_compact_document_scores_with_count
            ),
            log_prefix='combined out: ',
            log_level='debug'
        ) |
        "Summarise" >> beam.Map(
            lambda x: summarise_combined_document_scores_with_count(
                x, field_names
            )
        )
    )

    _ = (
        summary |
        "FlattenSummary" >> TransformAndLog(
            beam.FlatMap(partial(
                flatten_summary_results,
                field_names=field_names
            )),
            log_prefix='summary out: ',
            log_level='info'
        ) |
        "WriteSummaryToCsv" >> WriteDictCsv(
            os.path.join(opt.output_path, 'summary'),
            file_name_suffix='.csv',
            columns=DEFAULT_SUMMARY_OUTPUT_COLUMNS
        )
    )

    _ = (  # noqa: F841
        summary |
        "FormatGrobidEvaluation" >> beam.Map(
            lambda x: format_summarised_document_scores_as_grobid_report(
                x, field_names
            )
        ) |
        "WriteGrobidFormattedEvaluation" >> WriteToText(
            os.path.join(opt.output_path, 'grobid-formatted-summary'),
            file_name_suffix='.txt'
        )
    )


def add_main_args(parser):
    source_group = parser.add_argument_group('source')
    target_source_group = source_group.add_argument_group('target source')
    target_source_group.add_argument(
        '--target-file-list', type=str, required=True,
        help='path to target csv/tsv/lst file list'
    )
    target_source_group.add_argument(
        '--target-file-column', type=str, required=False,
        default='url',
        help='csv/tsv column (ignored for plain file list)'
    )

    prediction_source_group = source_group.add_argument_group(
        'prediction source'
    )
    prediction_source_group.add_argument(
        '--prediction-file-list', type=str, required=True,
        help='path to prediction csv/tsv/lst file list'
    )
    prediction_source_group.add_argument(
        '--prediction-file-column', type=str, required=False,
        default='url',
        help='csv/tsv column (ignored for plain file list)'
    )

    parser.add_argument(
        '--limit', type=int, required=False,
        help='limit the number of file pairs to process'
    )

    config_group = parser.add_argument_group('config')
    config_group.add_argument(
        '--xml-mapping', type=str,
        default=DEFAULT_XML_MAPPING_PATH,
        help='filename to the xml mapping configuration'
    )

    config_group.add_argument(
        '--evaluation-config', type=str,
        default=DEFAULT_EVALUATION_CONFIG_PATH,
        help='filename to the evaluation configuration'
    )

    config_group.add_argument(
        '--evaluation-yaml-config', type=str,
        default=DEFAULT_EVALUATION_YAML_FILENAME,
        help='filename to the evaluation configuration (yaml)'
    )

    config_group.add_argument(
        '--scoring-type-overrides', type=parse_scoring_type_overrides,
        default={},
        help=' '.join([
            'overrides for the scoring types (evaluation configuration).',
            'format: field1=scoring-type1,scoring-type2|field2=scoring-type1'
        ])
    )

    parser.add_argument(
        '--fields',
        type=get_plus_minus_comma_separated_str_to_list_fn(
            DEFAULT_EXTRACTION_FIELDS
        ),
        default=DEFAULT_EXTRACTION_FIELDS,
        help='comma separated list of fields to process'
    )

    parser.add_argument(
        '--measures',
        type=get_plus_minus_comma_separated_str_to_list_fn(
            DEFAULT_SCORE_MEASURES
        ),
        default=DEFAULT_SCORE_MEASURES,
        help='comma separated list of measures to process (valid values: %s)' % (
            ', '.join(ALL_SCORING_METHOD_NAMES)
        )
    )

    parser.add_argument(
        '--convert-to-lower', action='store_true',
        help='convert all text to lower case'
    )

    output_group = parser.add_argument_group('output')
    output_group.add_argument(
        '--output-path', required=True,
        help='Output directory to write results to.'
    )

    skip_errors_group = parser.add_argument_group('skip errors')
    skip_errors_group.add_argument(
        '--skip-errors', dest='skip_errors', action='store_true', default=False,
        help='skip and log evaluation error'
    )
    skip_errors_group.add_argument(
        '--no-skip-errors', dest='skip_errors', action='store_false',
        help='fail on evaluation error'
    )

    parser.add_argument(
        '--sequential', action='store_true', default=False,
        help='process output sequentially (mainly to produce the same output order)'
    )

    parser.add_argument(
        '--debug', action='store_true', default=False,
        help='enable debug output'
    )


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    add_main_args(parser)
    add_cloud_args(parser)
    direct_runner_parser = parser.add_argument_group('direct runner', conflict_handler='resolve')
    DirectOptions._add_argparse_args(direct_runner_parser)  # pylint: disable=protected-access
    worker_parser = parser.add_argument_group('worker', conflict_handler='resolve')
    WorkerOptions._add_argparse_args(worker_parser)  # pylint: disable=protected-access

    args = parser.parse_args(argv)

    if args.debug:
        logging.getLogger('sciencebeam_judge').setLevel('DEBUG')

    process_cloud_args(
        args, args.output_path,
        name='sciencebeam-judge'
    )

    get_logger().info('args: %s', args)

    return args


def run(argv=None):
    register_functions()

    args = parse_args(argv)

    # We use the save_main_session option because one or more DoFn's in this
    # workflow rely on global context (e.g., a module imported at module level).
    pipeline_options = PipelineOptions.from_dictionary({
        key: value
        for key, value in vars(args).items()
        if value is not None
    })
    pipeline_options.view_as(SetupOptions).save_main_session = True

    with beam.Pipeline(args.runner, options=pipeline_options) as p:
        configure_pipeline(p, args)

        # Execute the pipeline and wait until it is completed.


if __name__ == '__main__':
    logging.basicConfig(level='INFO')

    run()
