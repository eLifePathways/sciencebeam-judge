import logging

from lxml.builder import ElementMaker

from .utils import parse_xml_node

# false positive not-callable for lxml.builder.TEI_E
# pylint: disable=not-callable


LOGGER = logging.getLogger(__name__)

TEI_NS = 'http://www.tei-c.org/ns/1.0'
TEI_NS_PREFIX = '{%s}' % TEI_NS

TEI_NS_MAP = {
    'tei': TEI_NS
}

TEI_E = ElementMaker(namespace=TEI_NS, nsmap={
    None: TEI_NS
})


DOI_1 = '10.12345/abc/1'
HTTPS_DOI_URL_PREFIX = 'https://doi.org/'

LABEL_1 = 'Label 1'
TEXT_1 = 'Some text 1'

EMAIL_1 = 'name1@test'
EMAIL_2 = 'name2@test'

COORDS = 'coords'
COORDS_1 = '101,102,103,104,105'


class TestTei:
    class TestJatsCorrespondingAuthor:
        def test_should_find_corresponding_author_via_corresp_role(
                self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.teiHeader(
                TEI_E.fileDesc(TEI_E.sourceDesc(TEI_E.biblStruct(TEI_E.analytic(
                    TEI_E.author(
                        {'role': 'corresp'},
                        TEI_E.persName(TEI_E.forename('First1'), TEI_E.surname('Sur1')),
                        TEI_E.email(EMAIL_1)
                    ),
                    TEI_E.author(
                        TEI_E.persName(TEI_E.forename('First2'), TEI_E.surname('Sur2')),
                        TEI_E.email(EMAIL_2)
                    )
                ))))
            ))
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

    class TestTeiAuthorAffiliation:
        def test_should_parse_single_affiliation(
                self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.teiHeader(
                TEI_E.fileDesc(TEI_E.sourceDesc(TEI_E.biblStruct(TEI_E.analytic(
                    TEI_E.author(TEI_E.affiliation(
                        TEI_E.note(
                            {'type': 'raw_affiliation'},
                            TEI_E.label('a'),
                            ' Institution 1, City 1, Country 1'
                        ),
                        TEI_E.orgName({'type': 'institution'}, 'Institution 1'),
                        TEI_E.address(
                            TEI_E.settlement('City 1'),
                            TEI_E.country('Country 1')
                        )
                    ))
                ))))
            ))
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

        def test_should_join_affiliation_text_with_same_label(
                self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.teiHeader(
                TEI_E.fileDesc(TEI_E.sourceDesc(TEI_E.biblStruct(TEI_E.analytic(
                    TEI_E.author(
                        TEI_E.affiliation(
                            TEI_E.note({'type': 'raw_affiliation'}, TEI_E.label('a'), ' Part 1')
                        ),
                        TEI_E.affiliation(
                            TEI_E.note({'type': 'raw_affiliation'}, TEI_E.label('a'), ' Part 2')
                        ),
                        TEI_E.affiliation(
                            TEI_E.note({'type': 'raw_affiliation'}, TEI_E.label('b'), ' Other')
                        )
                    )
                ))))
            ))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'affiliation_text',
                    'affiliation_by_label_text'
                ]
            )
            assert result.get('affiliation_text') == ['a Part 1', 'a Part 2', 'b Other']
            assert result.get('affiliation_by_label_text') == ['a Part 1 Part 2', 'b Other']

    class TestTeiReferenceAuthorNames:
        def test_should_parse_tei_ref_authors(self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.text(TEI_E.back(TEI_E.div(TEI_E.listBibl(
                TEI_E.biblStruct(TEI_E.analytic(TEI_E.author(TEI_E.persName(
                    TEI_E.forename('GivenName1.1', type='first'),
                    TEI_E.surname('Surname1.1')
                )), TEI_E.author(TEI_E.persName(
                    TEI_E.forename('GivenName1.2', type='first'),
                    TEI_E.surname('Surname1.2')
                )))),
                TEI_E.biblStruct(TEI_E.analytic(TEI_E.author(TEI_E.persName(
                    TEI_E.forename('GivenName2.1'),
                    TEI_E.surname('Surname2.1')
                ))))
            )))))
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

        def test_should_normalize_tei_ref_author_name(self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.text(TEI_E.back(TEI_E.div(TEI_E.listBibl(
                TEI_E.biblStruct(TEI_E.analytic(TEI_E.author(TEI_E.persName(
                    TEI_E.forename('A', type='first'),
                    TEI_E.forename('M', type='middle'),
                    TEI_E.surname('Smith')
                ))))
            )))))
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
                {'items': ['AM']},
            ]

    class TestTeiReferenceTitle:
        def test_should_parse_tei_journal_article_and_source(
                self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.text(TEI_E.back(TEI_E.div(TEI_E.listBibl(
                TEI_E.biblStruct(TEI_E.analytic(
                    TEI_E.title('Article 1', level='a', type='main'),
                ), TEI_E.monogr(
                    TEI_E.title('Journal 1', level='j')
                ))
            )))))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'first_reference_title',
                    'reference_title',
                    'reference_source',
                    'reference_publication_type'
                ]
            )
            assert result.get('first_reference_title') == ['Article 1']
            assert result.get('reference_title') == ['Article 1']
            assert result.get('reference_source') == ['Journal 1']
            assert result.get('reference_publication_type') == ['journal']

        def test_should_parse_tei_book_chapter_and_source(
                self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.text(TEI_E.back(TEI_E.div(TEI_E.listBibl(
                TEI_E.biblStruct(TEI_E.analytic(
                    TEI_E.title('Chapter 1', level='a', type='main')
                ), TEI_E.monogr(
                    TEI_E.title('Book 1', level='m')
                ))
            )))))
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
            xml = TEI_E.TEI(TEI_E.text(TEI_E.back(TEI_E.div(TEI_E.listBibl(
                TEI_E.biblStruct(TEI_E.analytic(
                    TEI_E.title('Chapter 1', level='a', type='main'),
                    TEI_E.idno('doi1', type='DOI'),
                    TEI_E.idno('pmid1', type='PMID'),
                    TEI_E.idno('pmcid1', type='PMCID')
                ), TEI_E.monogr(
                    TEI_E.title('Book 1', level='m')
                ))
            )))))
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

    class TestTeiAbstractText:
        def test_should_return_without_paragraph(self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.teiHeader(TEI_E.profileDesc(TEI_E.abstract(
                'abstract1'
            ))))
            result = parse_xml_node(xml, xml_mapping=default_xml_mapping)
            assert result.get('abstract') == ['abstract1']

        def test_should_return_with_div_and_paragraph(self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.teiHeader(TEI_E.profileDesc(TEI_E.abstract(TEI_E.div(
                TEI_E.p('abstract1')
            )))))
            result = parse_xml_node(xml, xml_mapping=default_xml_mapping)
            assert result.get('abstract') == ['abstract1']

        def test_should_ignore_first_head(self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.teiHeader(TEI_E.profileDesc(TEI_E.abstract(TEI_E.div(
                TEI_E.head('Abstract'),
                TEI_E.p('abstract1')
            )))))
            result = parse_xml_node(xml, xml_mapping=default_xml_mapping)
            assert result.get('abstract') == ['abstract1']

        def test_not_should_ignore_further_head_elements(self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.teiHeader(TEI_E.profileDesc(TEI_E.abstract(
                TEI_E.div(TEI_E.head('Abstract')),
                TEI_E.div(TEI_E.head('Sub:'), TEI_E.p('abstract1'))
            ))))
            result = parse_xml_node(xml, xml_mapping=default_xml_mapping)
            assert result.get('abstract') == ['Sub: abstract1']

        def test_should_return_multiple_abstracts_as_separate_items(
                self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.teiHeader(TEI_E.profileDesc(
                TEI_E.abstract(TEI_E.div(TEI_E.p('abstract1'))),
                TEI_E.abstract(TEI_E.div(TEI_E.p('resumo1')))
            )))
            result = parse_xml_node(xml, xml_mapping=default_xml_mapping)
            assert result.get('abstract') == ['abstract1', 'resumo1']

    class TestTeiBodyAndBackSections:
        def test_should_parse_body_and_back_sections(
                self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.text(
                TEI_E.body(TEI_E.div(
                    TEI_E.head('Section Title 1'),
                    TEI_E.p('Section Paragraph 1')
                )),
                TEI_E.back(TEI_E.div(
                    {'type': 'acknowledgement'},
                    TEI_E.div(
                        TEI_E.head('Acknowledgement Title'),
                        TEI_E.p('Acknowledgement Paragraph')
                    )
                ), TEI_E.div(
                    TEI_E.head('Section Title 2'),
                    TEI_E.p('Section Paragraph 2')
                ))
            ))
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
            xml = TEI_E.TEI(TEI_E.text(
                TEI_E.body(TEI_E.div(
                    TEI_E.head('Section Title 1'),
                    TEI_E.p('Section Paragraph 1a'),
                    TEI_E.p('Section Paragraph 1b'),
                    TEI_E.div(
                        TEI_E.head('Section Title 1.1'),
                        TEI_E.p('Section Paragraph 1.1a'),
                        TEI_E.p('Section Paragraph 1.1b')
                    )
                ), TEI_E.div(
                    TEI_E.head('Section Title 2'),
                    TEI_E.p('Section Paragraph 2a'),
                    TEI_E.p('Section Paragraph 2b')
                ))
            ))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'body_section_titles',
                    'body_section_paragraphs'
                ]
            )
            assert result.get('body_section_titles') == [
                'Section Title 1',
                'Section Title 1.1',
                'Section Title 2'
            ]
            assert result.get('body_section_paragraphs') == [
                'Section Paragraph 1a\nSection Paragraph 1b',
                'Section Paragraph 1.1a\nSection Paragraph 1.1b',
                'Section Paragraph 2a\nSection Paragraph 2b'
            ]

        def test_should_join_multiple_back_paragraph_blocks_of_same_section(
                self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.text(
                TEI_E.back(TEI_E.div(
                    TEI_E.head('Section Title 1'),
                    TEI_E.p('Section Paragraph 1a'),
                    TEI_E.p('Section Paragraph 1b'),
                    TEI_E.div(
                        TEI_E.head('Section Title 1.1'),
                        TEI_E.p('Section Paragraph 1.1a'),
                        TEI_E.p('Section Paragraph 1.1b')
                    )
                ), TEI_E.div(
                    TEI_E.head('Section Title 2'),
                    TEI_E.p('Section Paragraph 2a'),
                    TEI_E.p('Section Paragraph 2b')
                ))
            ))
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
            xml = TEI_E.TEI(TEI_E.text(
                TEI_E.body(TEI_E.div(
                    TEI_E.head('Section Title 1', {'n': 'S1.'}),
                    TEI_E.p('Section Paragraph 1')
                )),
                TEI_E.back(TEI_E.div(
                    {'type': 'acknowledgement'},
                    TEI_E.div(
                        TEI_E.head('Acknowledgement Title', {'n': 'A.'}),
                        TEI_E.p('Acknowledgement Paragraph')
                    )
                ), TEI_E.div(
                    TEI_E.head('Section Title 2', {'n': 'S2.'}),
                    TEI_E.p('Section Paragraph 2')
                ))
            ))
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

        def test_should_join_label_with_section_title_using_formatting(
                self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.text(
                TEI_E.body(TEI_E.div(
                    TEI_E.head(TEI_E.hi('Section Title 1'), {'n': 'S1.'}),
                    TEI_E.p('Section Paragraph 1')
                )),
                TEI_E.back(TEI_E.div(
                    {'type': 'acknowledgement'},
                    TEI_E.div(
                        TEI_E.head(TEI_E.hi('Acknowledgement Title'), {'n': 'A.'}),
                        TEI_E.p('Acknowledgement Paragraph')
                    )
                ), TEI_E.div(
                    TEI_E.head(TEI_E.hi('Section Title 2'), {'n': 'S2.'}),
                    TEI_E.p('Section Paragraph 2')
                ))
            ))
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

    class TestTeiAcknowledgement:
        def test_should_parse_acknowledgement(
                self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.text(TEI_E.back(TEI_E.div(
                {'type': 'acknowledgement'},
                TEXT_1
            ))))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=['acknowledgement']
            )
            assert result.get('acknowledgement') == [TEXT_1]

    class TestTeiAbstractReferenceCitation:
        def test_should_find_body_reference_citation(self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.teiHeader(TEI_E.profileDesc(TEI_E.abstract(
                'References: ',
                TEI_E.ref({'type': 'bibr', 'target': '#ref1'}, '[1]'),
            ))))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'abstract_reference_citation_text'
                ]
            )
            assert result.get('abstract_reference_citation_text') == ['1']

    class TestTeiBodyReferenceCitation:
        def test_should_find_body_reference_citation(self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.text(TEI_E.body(TEI_E.div(TEI_E.p(
                'Reference to: [',
                TEI_E.ref({'type': 'bibr', 'target': '#ref1'}, '1'),
                ']'
            )))))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'body_reference_citation_text'
                ]
            )
            assert result.get('body_reference_citation_text') == ['1']

        def test_should_strip_brackets(self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.text(TEI_E.body(TEI_E.div(TEI_E.p(
                'References:',
                TEI_E.ref({'type': 'bibr', 'target': '#ref1'}, '[1]'),
                TEI_E.ref({'type': 'bibr', 'target': '#ref2'}, '(2)'),
                TEI_E.ref({'type': 'bibr', 'target': '#ref3'}, r'{3}')
            )))))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'body_reference_citation_text'
                ]
            )
            assert result.get('body_reference_citation_text') == ['1', '2', '3']

    class TestTeiAbstractAssetCitation:
        def test_should_find_body_asset_citation(self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.teiHeader(TEI_E.profileDesc(TEI_E.abstract(
                'Assets:',
                TEI_E.ref({'type': 'figure', 'target': '#fig_1'}, '[Figure 1]'),
                TEI_E.ref({'type': 'table'}, '[Table 1]')
            ))))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'abstract_asset_citation_text'
                ]
            )
            assert result.get('abstract_asset_citation_text') == ['Figure 1', 'Table 1']

    class TestTeiBodyAssetCitation:
        def test_should_find_body_asset_citation(self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.text(TEI_E.body(TEI_E.div(TEI_E.p(
                'Assets:',
                TEI_E.ref({'type': 'figure', 'target': '#fig_1'}, '[Figure 1]'),
                TEI_E.ref({'type': 'table'}, '[Table 1]')
            )))))
            result = parse_xml_node(
                xml,
                xml_mapping=default_xml_mapping,
                fields=[
                    'body_asset_citation_text'
                ]
            )
            assert result.get('body_asset_citation_text') == ['Figure 1', 'Table 1']

    class TestTeiStyles:
        def test_should_find_styles_in_abstract(
                self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.teiHeader(TEI_E.profileDesc(TEI_E.abstract(
                TEI_E.hi({'rend': 'italic'}, 'italic1'),
                TEI_E.hi({'rend': 'bold'}, 'bold1'),
                TEI_E.sub('subscript1'),
                TEI_E.sup('superscript1'),
                TEI_E.hi(
                    {'rend': 'italic'},
                    TEI_E.hi(
                        {'rend': 'bold'},
                        TEI_E.sub(TEI_E.sup('mixed1'))
                    )
                )
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

    class TestTeiFigure:
        def test_should_parse_figure_label_and_description_in_body_section(
                self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.text(TEI_E.body(TEI_E.figure(
                TEI_E.head(LABEL_1),
                TEI_E.figDesc(TEXT_1),
                TEI_E.graphic({COORDS: COORDS_1})
            ))))
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
            xml = TEI_E.TEI(TEI_E.text(TEI_E.body(TEI_E.div(TEI_E.div(TEI_E.figure(
                TEI_E.head(LABEL_1),
                TEI_E.figDesc(TEXT_1)
            ))))))
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
            xml = TEI_E.TEI(TEI_E.text(TEI_E.back(TEI_E.figure(
                TEI_E.head(LABEL_1),
                TEI_E.figDesc(TEXT_1)
            ))))
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

    class TestTeiTable:
        def test_should_parse_table_label_and_description_in_body_section(
                self, default_xml_mapping):
            xml = TEI_E.TEI(TEI_E.text(TEI_E.body(TEI_E.figure(
                {'type': 'table'},
                TEI_E.head(LABEL_1),
                TEI_E.figDesc(TEXT_1)
            ))))
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
            xml = TEI_E.TEI(TEI_E.text(TEI_E.body(TEI_E.div(TEI_E.div(TEI_E.figure(
                {'type': 'table'},
                TEI_E.head(LABEL_1),
                TEI_E.figDesc(TEXT_1)
            ))))))
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
            xml = TEI_E.TEI(TEI_E.text(TEI_E.back(TEI_E.figure(
                {'type': 'table'},
                TEI_E.head(LABEL_1),
                TEI_E.figDesc(TEXT_1)
            ))))
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
