import logging

from lxml.builder import E


from sciencebeam_judge.evaluation_config import (
    parse_evaluation_config,
    get_scoring_types_by_field_map_from_config
)
from sciencebeam_judge.evaluation.document_scoring import iter_score_document_fields
from sciencebeam_judge.parsing.xpath.jats_xpath_functions import (
    XLINK_HREF
)
from sciencebeam_judge.resources import DEFAULT_EVALUATION_CONFIG_PATH

from .utils import parse_xml_node

# false positive not-callable for lxml.builder.E
# pylint: disable=not-callable


LOGGER = logging.getLogger(__name__)


DOI_1 = '10.12345/abc/1'
HTTPS_DOI_URL_PREFIX = 'https://doi.org/'

LABEL_1 = 'Label 1'
TEXT_1 = 'Some text 1'

EMAIL_1 = 'name1@test'
EMAIL_2 = 'name2@test'

XML_LANG = '{http://www.w3.org/XML/1998/namespace}lang'

COORDS_NS = 'http://www.tei-c.org/ns/1.0'
COORDS_NS_PREFIX = '{%s}' % COORDS_NS
COORDS = COORDS_NS_PREFIX + 'coords'
COORDS_1 = '101,102,103,104,105'


class TestJats:
    class TestJatsCorrespondingAuthor:
        def test_should_find_corresponding_author_via_corresp_attribute(
                self, default_xml_mapping):
            xml = E.article(E.front(E('article-meta', E('contrib-group', *[
                E.contrib(
                    {'contrib-type': 'author', 'corresp': 'yes'},
                    E.name(E.surname('Sur1'), E('given-names', 'First1')),
                    E.email(EMAIL_1)
                ),
                E.contrib(
                    {'contrib-type': 'author'},
                    E.name(E.surname('Sur2'), E('given-names', 'First2')),
                    E.email(EMAIL_2)
                )
            ]))))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'author_surnames',
                    'author_given_names',
                    'author_full_names',
                    'author_emails',
                    'corresp_author_surnames',
                    'corresp_author_given_names',
                    'corresp_author_full_names',
                    'corresp_author_emails'
                ]
            )
            assert result.get('author_surnames') == ['Sur1', 'Sur2']
            assert result.get('author_given_names') == ['First1', 'First2']
            assert result.get('author_full_names') == ['First1 Sur1', 'First2 Sur2']
            assert result.get('author_emails') == [EMAIL_1, EMAIL_2]
            assert result.get('corresp_author_surnames') == ['Sur1']
            assert result.get('corresp_author_given_names') == ['First1']
            assert result.get('corresp_author_full_names') == ['First1 Sur1']
            assert result.get('corresp_author_emails') == [EMAIL_1]

        def test_should_find_email_from_author_notes(
                self, default_xml_mapping):
            xml = E.article(E.front(E('article-meta', *[
                E('contrib-group', *[
                    E.contrib(
                        {'contrib-type': 'author', 'corresp': 'yes'},
                        E.xref({'ref-type': 'corresp', 'rid': 'cor1'}, '*')
                    ),
                    E.contrib(
                        {'contrib-type': 'author'},
                        E.xref({'ref-type': 'other', 'rid': 'other1'}, '*')
                    )
                ]),
                E('author-notes', *[
                    E.corresp({'id': 'cor1'}, 'Corresponding author: ', E.email(EMAIL_1)),
                    E.fn({'id': 'other1'}, 'Other author: ', E.email(EMAIL_2))
                ])
            ])))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'author_emails',
                    'corresp_author_emails'
                ]
            )
            assert result.get('author_emails') == [EMAIL_1, EMAIL_2]
            assert result.get('corresp_author_emails') == [EMAIL_1]

    class TestJatsAuthorAffiliation:
        def test_should_parse_single_affiliation(
                self, default_xml_mapping):
            xml = E.article(E.front(E('article-meta', E('contrib-group', E.aff(
                E.label('a'),
                E.institution('Institution 1'),
                ', City 1, ',
                E.country('Country 1')
            )))))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'affiliation_text',
                    'affiliation_label',
                    'affiliation_institution',
                    'affiliation_country'
                ]
            )
            assert result.get('affiliation_text') == ['a Institution 1, City 1, Country 1']
            assert result.get('affiliation_label') == ['a']
            assert result.get('affiliation_institution') == ['Institution 1']
            assert result.get('affiliation_country') == ['Country 1']

    class TestJatsReferenceText:
        def test_should_get_reference_text(self, default_xml_mapping):
            xml = E.article(E.back(E(
                'ref-list',
                E.ref('reference 1'),
                E.ref('reference 2')
            )))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'first_reference_text',
                    'reference_text'
                ]
            )
            assert result.get('first_reference_text') == [
                'reference 1'
            ]
            assert result.get('reference_text') == [
                'reference 1',
                'reference 2'
            ]

        def test_should_get_reference_text_for_multiple_ref_lists(self, default_xml_mapping):
            xml = E.article(E.back(
                E('ref-list', E.ref('reference 1')),
                E('ref-list', E.ref('reference 2'))
            ))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'first_reference_text',
                    'reference_text'
                ]
            )
            assert result.get('first_reference_text') == [
                'reference 1'
            ]
            assert result.get('reference_text') == [
                'reference 1',
                'reference 2'
            ]

    class TestJatsReferenceAuthorNames:
        def test_should_parse_mixed_style_jats(self, default_xml_mapping):
            xml = E.article(E.back(E(
                'ref-list',
                E.ref(E('mixed-citation', E(
                    'string-name',
                    E.surname('Surname1.1'),
                    E('given-names', 'GivenName1.1')
                ), E(
                    'string-name',
                    E.surname('Surname1.2'),
                    E('given-names', 'GivenName1.2')
                ))),
                E.ref(E('mixed-citation', E(
                    'string-name',
                    E.surname('Surname2.1'),
                    E('given-names', 'GivenName2.1')
                )))
            )))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'reference_author_surnames',
                    'reference_author_given_names',
                    'reference_author_full_names'
                ]
            )
            assert result.get('reference_author_surnames') == [
                {'items': ['Surname1.1', 'Surname1.2']},
                {'items': ['Surname2.1']}
            ]
            assert result.get('reference_author_given_names') == [
                {'items': ['GivenName1.1', 'GivenName1.2']},
                {'items': ['GivenName2.1']}
            ]
            assert result.get('reference_author_full_names') == [
                {'items': ['GivenName1.1 Surname1.1', 'GivenName1.2 Surname1.2']},
                {'items': ['GivenName2.1 Surname2.1']}
            ]

        def test_should_parse_element_style_jats(self, default_xml_mapping):
            xml = E.article(E.back(E(
                'ref-list',
                E.ref(E('element-citation', E('person-group', E.name(
                    E.surname('Surname1.1'),
                    E('given-names', 'GivenName1.1')
                ), E.name(
                    E.surname('Surname1.2'),
                    E('given-names', 'GivenName1.2')
                )))),
                E.ref(E('element-citation', E('person-group', E.name(
                    E.surname('Surname2.1'),
                    E('given-names', 'GivenName2.1')
                ))))
            )))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'reference_author_surnames',
                    'reference_author_given_names',
                    'reference_author_full_names'
                ]
            )
            assert result.get('reference_author_surnames') == [
                {'items': ['Surname1.1', 'Surname1.2']},
                {'items': ['Surname2.1']}
            ]
            assert result.get('reference_author_given_names') == [
                {'items': ['GivenName1.1', 'GivenName1.2']},
                {'items': ['GivenName2.1']}
            ]
            assert result.get('reference_author_full_names') == [
                {'items': ['GivenName1.1 Surname1.1', 'GivenName1.2 Surname1.2']},
                {'items': ['GivenName2.1 Surname2.1']}
            ]

        def test_should_normalize_author_name(self, default_xml_mapping):
            xml = E.article(E.back(E(
                'ref-list',
                E.ref(E('mixed-citation', E(
                    'string-name',
                    E.surname('Smith'),
                    E('given-names', 'A. M.')
                )))
            )))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'reference_author_surnames',
                    'reference_author_given_names',
                    'reference_author_full_names'
                ]
            )
            assert result.get('reference_author_surnames') == [
                {'items': ['Smith']}
            ]
            assert result.get('reference_author_full_names') == [
                {'items': ['AM Smith']}
            ]
            assert result.get('reference_author_given_names') == [
                {'items': ['AM']}
            ]

    class TestJatsReferenceTitle:
        def test_should_parse_mixed_style_journal_article_title_and_source(
                self, default_xml_mapping):
            xml = E.article(E.back(E(
                'ref-list',
                E.ref(E.label('1'), E(
                    'mixed-citation',
                    E('article-title', 'Article 1'),
                    E.source('Journal 1'),
                    {'publication-type': 'journal'}
                ))
            )))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'reference_title',
                    'reference_source',
                    'reference_publication_type'
                ]
            )
            assert result.get('reference_title') == ['Article 1']
            assert result.get('reference_source') == ['Journal 1']
            assert result.get('reference_publication_type') == ['journal']

        def test_should_parse_mixed_style_book_chapter_title_and_source(
                self, default_xml_mapping):
            xml = E.article(E.back(E(
                'ref-list',
                E.ref(E.label('1'), E(
                    'mixed-citation',
                    E('chapter-title', 'Chapter 1'),
                    E.source('Book 1'),
                    {'publication-type': 'book'}
                ))
            )))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'reference_title',
                    'reference_source',
                    'reference_publication_type'
                ]
            )
            assert result.get('reference_title') == ['Chapter 1']
            assert result.get('reference_source') == ['Book 1']
            assert result.get('reference_publication_type') == ['book']

    class TestJatsReferenceExternalIdentifiers:
        def test_should_parse_mixed_style_external_identifiers(
                self, default_xml_mapping):
            xml = E.article(E.back(E(
                'ref-list',
                E.ref(E.label('1'), E(
                    'mixed-citation',
                    E('pub-id', 'doi1', {'pub-id-type': 'doi'}),
                    E('pub-id', 'pmid1', {'pub-id-type': 'pmid'}),
                    E('pub-id', 'pmcid1', {'pub-id-type': 'pmcid'})
                ))
            )))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'first_reference_doi',
                    'reference_doi',
                    'first_reference_pmid',
                    'reference_pmid',
                    'first_reference_pmcid',
                    'reference_pmcid'
                ]
            )
            assert result.get('first_reference_doi') == ['doi1']
            assert result.get('reference_doi') == ['doi1']
            assert result.get('first_reference_pmid') == ['pmid1']
            assert result.get('reference_pmid') == ['pmid1']
            assert result.get('first_reference_pmcid') == ['pmcid1']
            assert result.get('reference_pmcid') == ['pmcid1']

        def test_should_parse_doi_from_doi_url(
                self, default_xml_mapping):
            xml = E.article(E.back(E(
                'ref-list',
                E.ref(E.label('1'), E(
                    'mixed-citation',
                    E('ext-link', 'Some link text', {
                        'ext-link-type': 'uri',
                        XLINK_HREF: HTTPS_DOI_URL_PREFIX + DOI_1
                    })
                ))
            )))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'first_reference_doi',
                    'reference_doi'
                ]
            )
            assert result.get('first_reference_doi') == [DOI_1]
            assert result.get('reference_doi') == [DOI_1]

    class TestJatsBodyAndBackSections:
        def test_should_parse_body_and_back_sections(
                self, default_xml_mapping):
            xml = E.article(
                E.body(E.sec(
                    E.title('Section Title 1'),
                    E.p('Section Paragraph 1')
                )),
                E.back(E.ack(
                    E.title('Acknowledgement Title'),
                    E.p('Acknowledgement Paragraph')
                ), E.sec(
                    E.title('Section Title 2'),
                    E.p('Section Paragraph 2')
                ))
            )
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'body_section_titles',
                    'body_section_paragraphs',
                    'back_section_titles',
                    'back_section_paragraphs',
                    'all_section_titles',
                    'all_section_paragraphs',
                    'first_body_section_paragraph',
                    'first_back_section_paragraph',
                    'first_all_section_paragraph'
                ]
            )
            assert result.get('body_section_titles') == ['Section Title 1']
            assert result.get('body_section_paragraphs') == ['Section Paragraph 1']
            assert result.get('back_section_titles') == ['Acknowledgement Title', 'Section Title 2']
            assert result.get('back_section_paragraphs') == [
                'Acknowledgement Paragraph', 'Section Paragraph 2'
            ]
            assert result.get('all_section_titles') == [
                'Section Title 1',
                'Acknowledgement Title', 'Section Title 2'
            ]
            assert result.get('all_section_paragraphs') == [
                'Section Paragraph 1',
                'Acknowledgement Paragraph', 'Section Paragraph 2'
            ]
            assert result.get('first_body_section_paragraph') == (
                result.get('body_section_paragraphs')[:1]
            )
            assert result.get('first_back_section_paragraph') == (
                result.get('back_section_paragraphs')[:1]
            )
            assert result.get('first_all_section_paragraph') == (
                result.get('all_section_paragraphs')[:1]
            )

        def test_should_join_multiple_body_paragraph_blocks_of_same_section(
                self, default_xml_mapping):
            xml = E.article(
                E.body(E.sec(
                    E.title('Section Title 1'),
                    E.p('Section Paragraph 1a'),
                    E.p('Section Paragraph 1b'),
                    E.sec(
                        E.title('Section Title 1.1'),
                        E.p('Section Paragraph 1.1a'),
                        E.p('Section Paragraph 1.1b')
                    )
                ), E.sec(
                    E.title('Section Title 2'),
                    E.p('Section Paragraph 2a'),
                    E.p('Section Paragraph 2b')
                ))
            )
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'body_section_titles',
                    'body_section_paragraphs'
                ]
            )
            assert result.get('body_section_titles') == [
                'Section Title 1', 'Section Title 1.1', 'Section Title 2'
            ]
            assert result.get('body_section_paragraphs') == [
                'Section Paragraph 1a\nSection Paragraph 1b',
                'Section Paragraph 1.1a\nSection Paragraph 1.1b',
                'Section Paragraph 2a\nSection Paragraph 2b'
            ]

        def test_should_join_multiple_back_paragraph_blocks_of_same_section(
                self, default_xml_mapping):
            xml = E.article(
                E.back(E.sec(
                    E.title('Section Title 1'),
                    E.p('Section Paragraph 1a'),
                    E.p('Section Paragraph 1b'),
                    E.sec(
                        E.title('Section Title 1.1'),
                        E.p('Section Paragraph 1.1a'),
                        E.p('Section Paragraph 1.1b')
                    )
                ), E.sec(
                    E.title('Section Title 2'),
                    E.p('Section Paragraph 2a'),
                    E.p('Section Paragraph 2b')
                ))
            )
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'back_section_titles',
                    'back_section_paragraphs'
                ]
            )
            assert result.get('back_section_titles') == [
                'Section Title 1', 'Section Title 1.1', 'Section Title 2'
            ]
            assert result.get('back_section_paragraphs') == [
                'Section Paragraph 1a\nSection Paragraph 1b',
                'Section Paragraph 1.1a\nSection Paragraph 1.1b',
                'Section Paragraph 2a\nSection Paragraph 2b'
            ]

        def test_should_join_label_with_section_title(
                self, default_xml_mapping):
            xml = E.article(
                E.body(E.sec(
                    E.label('S1.'),
                    E.title('Section Title 1'),
                    E.p('Section Paragraph 1')
                )),
                E.back(E.ack(
                    E.label('A.'),
                    E.title('Acknowledgement Title'),
                    E.p('Acknowledgement Paragraph')
                ), E.sec(
                    E.label('S2.'),
                    E.title('Section Title 2'),
                    E.p('Section Paragraph 2')
                ))
            )
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'body_section_labels',
                    'body_section_titles',
                    'body_section_label_titles',
                    'back_section_labels',
                    'back_section_titles',
                    'back_section_label_titles',
                    'all_section_labels',
                    'all_section_titles',
                    'all_section_label_titles'
                ]
            )
            assert result.get('body_section_labels') == ['S1.']
            assert result.get('body_section_titles') == ['Section Title 1']
            assert result.get('body_section_label_titles') == ['S1. Section Title 1']
            assert result.get('back_section_labels') == ['A.', 'S2.']
            assert result.get('back_section_titles') == [
                'Acknowledgement Title', 'Section Title 2'
            ]
            assert result.get('back_section_label_titles') == [
                'A. Acknowledgement Title', 'S2. Section Title 2'
            ]
            assert result.get('all_section_labels') == ['S1.', 'A.', 'S2.']
            assert result.get('all_section_titles') == [
                'Section Title 1',
                'Acknowledgement Title',
                'Section Title 2'
            ]
            assert result.get('all_section_label_titles') == [
                'S1. Section Title 1',
                'A. Acknowledgement Title',
                'S2. Section Title 2'
            ]

    class TestJatsAcknowledgement:
        def test_should_parse_acknowledgement(
                self, default_xml_mapping):
            xml = E.article(E.back(E.ack(
                TEXT_1
            )))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=['acknowledgement']
            )
            assert result.get('acknowledgement') == [TEXT_1]

    class TestJatsAbstract:
        def test_should_parse_single_abstract(self, default_xml_mapping):
            xml = E.article(E.front(E('article-meta', E.abstract(
                E.p(TEXT_1)
            ))))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=['abstract']
            )
            assert result.get('abstract') == [TEXT_1]

        def test_should_parse_trans_abstract_as_separate_item(
                self, default_xml_mapping):
            xml = E.article(E.front(E(
                'article-meta',
                E.abstract(E.p('Abstract 1')),
                E('trans-abstract', {XML_LANG: 'pt'}, E.p('Resumo 1')),
                E('trans-abstract', {XML_LANG: 'es'}, E.p('Resumen 1'))
            )))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=['abstract']
            )
            assert result.get('abstract') == ['Abstract 1', 'Resumo 1', 'Resumen 1']

        def test_should_parse_trans_abstract_without_abstract(
                self, default_xml_mapping):
            xml = E.article(E.front(E(
                'article-meta',
                E('trans-abstract', {XML_LANG: 'pt'}, E.p('Resumo 1'))
            )))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=['abstract']
            )
            assert result.get('abstract') == ['Resumo 1']

        def test_should_parse_multiple_abstracts_as_separate_items(
                self, default_xml_mapping):
            xml = E.article(E.front(E(
                'article-meta',
                E.abstract({XML_LANG: 'es'}, E.p('Resumen 1')),
                E.abstract({XML_LANG: 'en'}, E.p('Abstract 1'))
            )))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=['abstract']
            )
            assert result.get('abstract') == ['Resumen 1', 'Abstract 1']

        def test_should_match_translated_abstracts_in_any_order_using_default_scoring_types(
                self, default_xml_mapping):
            expected_xml = E.article(E.front(E(
                'article-meta',
                E.abstract(E.p('Abstract 1')),
                E('trans-abstract', {XML_LANG: 'pt'}, E.p('Resumo 1'))
            )))
            actual_xml = E.article(E.front(E(
                'article-meta',
                E.abstract(E.p('Resumo 1')),
                E('trans-abstract', {XML_LANG: 'en'}, E.p('Abstract 1'))
            )))
            scoring_types_by_field_map = get_scoring_types_by_field_map_from_config(
                parse_evaluation_config(DEFAULT_EVALUATION_CONFIG_PATH)
            )
            assert scoring_types_by_field_map['abstract'] == ['string', 'partial_ulist']
            scores = list(iter_score_document_fields(
                parse_xml_node(
                    expected_xml, xml_mapping=default_xml_mapping, fields=['abstract']
                ),
                parse_xml_node(
                    actual_xml, xml_mapping=default_xml_mapping, fields=['abstract']
                ),
                scoring_types_by_field_map=scoring_types_by_field_map,
                field_names=['abstract'],
                measures=['exact']
            ))
            match_score_by_scoring_type = {
                score['scoring_type']: score['match_score']
                for score in scores
            }
            assert set(match_score_by_scoring_type.keys()) == {'string', 'partial_ulist'}
            assert match_score_by_scoring_type['string']['true_positive'] == 0
            assert match_score_by_scoring_type['partial_ulist']['true_positive'] == 2
            assert match_score_by_scoring_type['partial_ulist']['false_positive'] == 0
            assert match_score_by_scoring_type['partial_ulist']['false_negative'] == 0

    class TestJatsAbstractReferenceCitation:
        def test_should_find_body_reference_citation(self, default_xml_mapping):
            xml = E.article(E.front(E('article-meta', E.abstract(
                'Reference to: [',
                E.xref({'ref-type': 'bibr', 'rid': 'ref1'}, '1'),
                ']'
            ))))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'abstract_reference_citation_text'
                ]
            )
            assert result.get('abstract_reference_citation_text') == ['1']

    class TestJatsBodyReferenceCitation:
        def test_should_find_body_reference_citation(self, default_xml_mapping):
            xml = E.article(E.body(E.sec(E.p(
                'Reference to: [',
                E.xref({'ref-type': 'bibr', 'rid': 'ref1'}, '1'),
                ']'
            ))))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'body_reference_citation_text'
                ]
            )
            assert result.get('body_reference_citation_text') == ['1']

    class TestJatsAbstractAssetCitation:
        def test_should_find_body_asset_citation(self, default_xml_mapping):
            xml = E.article(E.front(E('article-meta', E.abstract(
                'Assets:',
                E.xref({'ref-type': 'fig', 'rid': 'ref1'}, 'Figure 1'),
                E.xref({'ref-type': 'table', 'rid': 'ref1'}, 'Table 1'),
            ))))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'abstract_asset_citation_text'
                ]
            )
            assert result.get('abstract_asset_citation_text') == ['Figure 1', 'Table 1']

    class TestJatsBodyAssetCitation:
        def test_should_find_body_asset_citation(self, default_xml_mapping):
            xml = E.article(E.body(E.sec(E.p(
                'Assets:',
                E.xref({'ref-type': 'fig', 'rid': 'ref1'}, 'Figure 1'),
                E.xref({'ref-type': 'table', 'rid': 'ref1'}, 'Table 1'),
            ))))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'body_asset_citation_text'
                ]
            )
            assert result.get('body_asset_citation_text') == ['Figure 1', 'Table 1']

    class TestJatsStyles:
        def test_should_find_styles_in_abstract(
                self, default_xml_mapping):
            xml = E.article(E.front(E('article-meta', E.abstract(
                E.italic('italic1'),
                E.bold('bold1'),
                E.sub('subscript1'),
                E.sup('superscript1'),
                E.italic(E.bold(E.sub(E.sup('mixed1'))))
            ))))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'abstract_style_italic',
                    'abstract_style_bold',
                    'abstract_style_subscript',
                    'abstract_style_superscript',
                ]
            )
            assert result.get('abstract_style_italic') == ['italic1', 'mixed1']
            assert result.get('abstract_style_bold') == ['bold1', 'mixed1']
            assert result.get('abstract_style_subscript') == ['subscript1', 'mixed1']
            assert result.get('abstract_style_superscript') == ['superscript1', 'mixed1']

    class TestJatsFigure:
        def test_should_parse_figure_label_and_description_in_body_section(
                self, default_xml_mapping):
            xml = E.article(E.body(E.fig(
                E.label(LABEL_1),
                E.caption(TEXT_1),
                E.graphic({COORDS: COORDS_1})
            )))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'figure_labels', 'figure_captions', 'figure_label_captions',
                    'figure_graphic_bbox',
                    'body_figure_labels', 'body_figure_captions', 'body_figure_label_captions',
                    'body_figure_graphic_bbox',
                ]
            )
            assert result.get('figure_labels') == [LABEL_1]
            assert result.get('figure_captions') == [TEXT_1]
            assert result.get('figure_label_captions') == [f'{LABEL_1} {TEXT_1}']
            assert result.get('figure_graphic_bbox') == [COORDS_1]
            assert result.get('body_figure_labels') == [LABEL_1]
            assert result.get('body_figure_captions') == [TEXT_1]
            assert result.get('body_figure_label_captions') == [f'{LABEL_1} {TEXT_1}']
            assert result.get('body_figure_graphic_bbox') == [COORDS_1]

        def test_should_parse_figure_label_and_description_in_nested_section(
                self, default_xml_mapping):
            xml = E.article(E.body(E.sec(E.sect(E.fig(
                E.label(LABEL_1),
                E.caption(TEXT_1)
            )))))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'figure_labels', 'figure_captions', 'figure_label_captions',
                    'body_figure_labels', 'body_figure_captions', 'body_figure_label_captions'
                ]
            )
            assert result.get('figure_labels') == [LABEL_1]
            assert result.get('figure_captions') == [TEXT_1]
            assert result.get('figure_label_captions') == [f'{LABEL_1} {TEXT_1}']
            assert result.get('body_figure_labels') == [LABEL_1]
            assert result.get('body_figure_captions') == [TEXT_1]
            assert result.get('body_figure_label_captions') == [f'{LABEL_1} {TEXT_1}']

        def test_should_parse_figure_label_and_description_in_back_section(
                self, default_xml_mapping):
            xml = E.article(E.back(E.fig(
                E.label(LABEL_1),
                E.caption(TEXT_1)
            )))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'figure_labels', 'figure_captions', 'figure_label_captions',
                    'body_figure_labels', 'body_figure_captions', 'body_figure_label_captions'
                ]
            )
            assert result.get('figure_labels') == [LABEL_1]
            assert result.get('figure_captions') == [TEXT_1]
            assert result.get('figure_label_captions') == [f'{LABEL_1} {TEXT_1}']
            assert result.get('body_figure_labels') == []
            assert result.get('body_figure_captions') == []
            assert result.get('body_figure_label_captions') == []

    class TestJatsTable:
        def test_should_parse_table_label_and_description_in_body_section(
                self, default_xml_mapping):
            xml = E.article(E.body(E('table-wrap', *[
                E.label(LABEL_1),
                E.caption(TEXT_1)
            ])))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'table_labels', 'table_captions', 'table_label_captions',
                    'body_table_labels', 'body_table_captions', 'body_table_label_captions'
                ]
            )
            assert result.get('table_labels') == [LABEL_1]
            assert result.get('table_captions') == [TEXT_1]
            assert result.get('table_label_captions') == [f'{LABEL_1} {TEXT_1}']
            assert result.get('body_table_labels') == [LABEL_1]
            assert result.get('body_table_captions') == [TEXT_1]
            assert result.get('body_table_label_captions') == [f'{LABEL_1} {TEXT_1}']

        def test_should_parse_table_label_and_description_in_nested_section(
                self, default_xml_mapping):
            xml = E.article(E.body(E.sec(E.sect(E('table-wrap', *[
                E.label(LABEL_1),
                E.caption(TEXT_1)
            ])))))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'table_labels', 'table_captions', 'table_label_captions',
                    'body_table_labels', 'body_table_captions', 'body_table_label_captions'
                ]
            )
            assert result.get('table_labels') == [LABEL_1]
            assert result.get('table_captions') == [TEXT_1]
            assert result.get('table_label_captions') == [f'{LABEL_1} {TEXT_1}']
            assert result.get('body_table_labels') == [LABEL_1]
            assert result.get('body_table_captions') == [TEXT_1]
            assert result.get('body_table_label_captions') == [f'{LABEL_1} {TEXT_1}']

        def test_should_parse_table_label_and_description_in_back_section(
                self, default_xml_mapping):
            xml = E.article(E.back(E('table-wrap', *[
                E.label(LABEL_1),
                E.caption(TEXT_1)
            ])))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'table_labels', 'table_captions', 'table_label_captions',
                    'body_table_labels', 'body_table_captions', 'body_table_label_captions'
                ]
            )
            assert result.get('table_labels') == [LABEL_1]
            assert result.get('table_captions') == [TEXT_1]
            assert result.get('table_label_captions') == [f'{LABEL_1} {TEXT_1}']
            assert result.get('body_table_labels') == []
            assert result.get('body_table_captions') == []
            assert result.get('body_table_label_captions') == []
