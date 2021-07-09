import pytest

from courier.config import get_config
from courier.extract.java_extractor import ExtractedIssue, JavaExtractor

CONFIG = get_config()


@pytest.mark.java
def test_java_extractor():
    extractor: JavaExtractor = JavaExtractor()
    filename = CONFIG.pdf_dir / '012656engo.pdf'
    issue: ExtractedIssue = extractor.extract_issue(filename)

    assert len(issue) == 35
    assert issue.pages[1].pdf_page_number == 2
    assert 'TREASURES' in issue.pages[1].content
    assert len(issue.pages[1].titles) == 1
    assert len([title for title, _ in issue.pages[1].titles if 'TREASURE' in title]) != 0


# TODO: Parametrize
@pytest.mark.java
def test_titles_on_correct_pages():
    extractor: JavaExtractor = JavaExtractor()
    filename = CONFIG.pdf_dir / '012656engo.pdf'
    issue: ExtractedIssue = extractor.extract_issue(filename)

    assert titles_in_content(issue)


def titles_in_content(issue: ExtractedIssue) -> bool:
    """Returns true iff for each page in `issue` all of the page's titles are contained within the page's content"""
    # pylint: disable=use-a-generator
    return all(
        [
            all([title in issue.pages[i].content for title in [title for title, _ in issue.pages[i].titles]])
            for i in range(0, len(issue))
        ]
    )


# FIXME: Compare with pdfbox extract
@pytest.mark.java
def test_extract_issue_returns_expected_content():
    extractor: JavaExtractor = JavaExtractor()
    filename = CONFIG.pdf_dir / '012656engo.pdf'
    issue: ExtractedIssue = extractor.extract_issue(filename)

    p = issue.pages[2].content
    with open(CONFIG.pages_dir / 'pdfbox/012656engo_0003.txt', 'r') as fp:
        text = fp.read().strip()

    assert p == text
