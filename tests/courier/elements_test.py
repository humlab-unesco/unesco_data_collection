import filecmp
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

import pytest
import untangle

from courier.config import get_config
from courier.elements import (
    Article,
    AssignArticlesToPages,
    CourierIssue,
    DoubleSpreadRightPage,
    IssueStatistics,
    Page,
    export_articles,
    get_pdf_issue_content,
    get_xml_issue_content,
    read_xml,
)
from courier.extract.java_extractor import ExtractedIssue

CONFIG = get_config()
# TODO: Mock


def test_read_xml_removes_control_chars():
    expected = '\n\\x01 \\x02 \\x03 \\x04 \\x05 \\x06 \\x07 \\x08\n\\x0b \\x0c \\x0e \\x0f \\x10 \\x11 \\x12 \\x13 \\x14 \\x15 \\x16 \\x17 \\x18 \\x19 \\x1a \\x1b \\x1c \\x1d \\x1e \\x1f\n'
    content = read_xml(Path('tests/fixtures/invalid_chars.xml'))

    assert isinstance(content, untangle.Element)
    assert content.content.cdata == expected


def test_get_xml_issue_content_return_expected_values():
    content: ExtractedIssue = get_xml_issue_content(courier_id='012656')
    assert isinstance(content, ExtractedIssue)
    assert 'SEPTEMBER 1966' in str(content.pages[2])


def test_get_xml_issue_content_with_invalid_id_raises_value_error():
    with pytest.raises(ValueError, match='Not a valid courier id'):
        get_xml_issue_content('0')
    with pytest.raises(ValueError, match='not in article index'):
        get_xml_issue_content('000000')


def test_get_pdf_issue_content_return_expected_values():
    content: ExtractedIssue = get_pdf_issue_content(courier_id='012656')
    assert isinstance(content, ExtractedIssue)
    assert 'SEPTEMBER 1966' in str(content.pages[2])


@pytest.mark.parametrize(
    'input_pn, input_text, expected_pn, expected_text',
    [
        (1, 'one', 1, 'one'),
        (2, 'two', 2, 'two'),
        (3, 3, 3, '3'),
    ],
)
def test_create_page(input_pn, input_text, expected_pn, expected_text):

    result = Page(input_pn, input_text)
    assert isinstance(result, Page)

    assert isinstance(result.page_number, int)
    assert result.page_number == expected_pn

    assert isinstance(result.text, str)
    assert result.text == expected_text


def test_page_str_returns_expected():
    page = Page(page_number=1, text='test string')
    assert str(page) == 'test string'


def test_create_article():
    courier_issue: CourierIssue = CourierIssue('012656')

    assert courier_issue.courier_id == '012656'
    assert courier_issue.num_articles == 5
    assert len(courier_issue) == 36
    assert courier_issue.double_pages == [18]

    article: Optional[Article] = courier_issue.get_article('61469')
    assert article is None

    article: Article = courier_issue.articles[0]
    assert article.courier_id == '012656'
    assert article.record_number == 15043
    assert 'Bronze miniatures from ancient Sardinia' in article.catalogue_title
    assert article.year == 1966


# @pytest.mark.legacy
# def test_create_courier_issue():
#     courier_issue = CourierIssue('061468')
#     assert isinstance(courier_issue, CourierIssue)

#     assert courier_issue.num_articles == 3
#     assert len(courier_issue) == 36
#     assert courier_issue.double_pages == [10, 17]


def test_create_non_existing_issue_raises_value_error():
    with pytest.raises(ValueError, match='Not a valid courier id'):
        CourierIssue('0')
    with pytest.raises(ValueError, match='not in article index'):
        CourierIssue('000000')


# @pytest.mark.legacy
# @pytest.mark.parametrize(
#     'courier_id, expected',
#     [
#         ('061468', [10, 17]),
#         ('069916', [10, 11, 24]),
#         ('125736', []),  # no double pages
#         ('110425', []),  # excluded
#     ],
# )
# def test_courier_issues_has_correct_double_pages(courier_id, expected):
#     result = CourierIssue(courier_id).double_pages
#     assert result == expected


# @pytest.mark.skip('deprecated')
# def test_courier_issue_has_correct_index():
#     courier_issue = CourierIssue('061468')
#     assert not courier_issue.index.empty
#     assert courier_issue.index.shape == (3, 5)


# @pytest.mark.legacy
# @pytest.mark.parametrize(
#     'courier_id, pattern, expected',
#     [
#         ('061468', 'MARCH 1964', [(1, '1'), (3, '3')]),
#         ('061468', r'a.*open.*world', [(1, '1')]),
#         ('061468', 'nonmatchingpattern', []),
#         ('074891', 'drought over africa', [(3, '3'), (45, '45'), (67, '67')]),
#     ],
# )
# def test_courier_issue_find_pattern_returns_expected_values(courier_id, pattern, expected):
#     result = CourierIssue(courier_id).find_pattern(pattern)
#     assert result == expected


def test_courier_issue_get_page_when_issue_has_double_pages_returns_expected():
    courier_issue = CourierIssue('069916')
    assert courier_issue._pdf_double_page_numbers == [10, 11, 24]  # pylint: disable=protected-access
    assert courier_issue.double_pages == [10, 12, 26]

    assert courier_issue.get_page(11) == courier_issue.__getitem__(10) == courier_issue[10]

    assert isinstance(courier_issue.get_page(11), DoubleSpreadRightPage)
    assert isinstance(courier_issue.get_page(13), DoubleSpreadRightPage)
    assert isinstance(courier_issue.get_page(27), DoubleSpreadRightPage)

    assert courier_issue.get_page(11).text == courier_issue.get_page(13).text == courier_issue.get_page(27).text == ''


# @pytest.mark.skip('deprecated')
# def test_courier_issue_pages_when_issue_has_double_pages_returns_expected():
#     courier_issue = CourierIssue('069916')
#     pages = [p for p in courier_issue.pages]
#     assert len(pages) == courier_issue.num_pages
#     assert pages[8].text != pages[9].text == pages[10].text == pages[11].text != pages[12].text


# 069916;"10 11 24"
def test_to_pdf_page_number():
    issue = CourierIssue('012656')
    assert issue.to_pdf_page_number(15) == 14
    assert issue.to_pdf_page_number(18) == 17
    assert issue.to_pdf_page_number(19) == 17
    assert issue.to_pdf_page_number(20) == 18
    assert issue.to_pdf_page_number(21) == 19


# TODO
# test AssignArticlesToPages
# test ConsolidateArticleTexts
# test ExtractArticles assigns articles to issue pages

# pytest.mark.skip('temp')
# def test_main():

#     ExtractArticles.extract(issue)
#     assert IssueStatistics(issue).assigned_pages == 22


def test_issue_statistics_has_expected_values():
    issue = CourierIssue('012656')
    assert IssueStatistics(issue).assigned_pages == 0
    assert IssueStatistics(issue).expected_article_pages == 23
    assert IssueStatistics(issue).number_of_articles == 5
    assert IssueStatistics(issue).total_pages == 36


def test_issue_has_no_assigned_pages_as_default():
    issue = CourierIssue('012656')
    assert IssueStatistics(issue).assigned_pages == 0


# FIXME: Check this
def test_AssignArticlesToPages_assignes_expected_pages_to_issue():
    issue = CourierIssue('012656')
    AssignArticlesToPages().assign(issue)
    assert issue.get_assigned_pages() == {
        7,
        8,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
        29,
        30,
        31,
    }
    assert IssueStatistics(issue).assigned_pages == 22
    assert IssueStatistics(issue).consolidated_pages == 0

    # assert len(issue.get_consolidated_pages()) == 0
    # assert len(issue.get_assigned_pages()) == 22
    # ConsolidateArticleTexts().consolidate(issue)
    # assert len(issue.get_consolidated_pages()) == 22
    # assert IssueStatistics(issue).assigned_pages == 22


def test_issue_has_no_consolidated_pages_as_default():
    issue = CourierIssue('012656')
    assert IssueStatistics(issue).consolidated_pages == 0


def test_ConsolidateArticleTexts():
    issue = CourierIssue('012656')
    assert issue is not None


def test_export_articles_generates_expected_output():
    with TemporaryDirectory() as output_dir:
        export_articles('012656', output_dir)
        assert len(sorted(Path(output_dir).glob('*.txt'))) == 5
        assert filecmp.dircmp(output_dir, CONFIG.test_files_dir / 'expected/export_articles').diff_files == []
        assert len(filecmp.dircmp(output_dir, CONFIG.test_files_dir / 'not_expected').diff_files) == 1
