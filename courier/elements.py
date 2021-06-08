from courier.extract.java_extractor import ExtractedIssue, JavaExtractor
import io
import os
import re
import warnings
from dataclasses import dataclass
from typing import Iterator, List, Mapping, Optional, Tuple, Union

import untangle

from courier.config import get_config
from courier.utils import valid_xml

CONFIG = get_config()


def read_xml(filename: Union[str, bytes, os.PathLike]) -> untangle.Element:
    with open(filename, 'r') as fp:
        content = fp.read()
        content = valid_xml(content)
        xml = io.StringIO(content)
        element = untangle.parse(xml)
        return element


# FIXME: Unnecessary checks
def get_xml_issue_content(courier_id: str) -> untangle.Element:
    if len(courier_id) != 6:
        raise ValueError(f'Not a valid courier id "{courier_id}')
    if courier_id not in CONFIG.article_index.courier_id.values:
        raise ValueError(f'{courier_id} not in article index')
    return read_xml(list(CONFIG.xml_dir.glob(f'{courier_id}*.xml'))[0])

def get_pdf_issue_content(courier_id: str) -> ExtractedIssue:

    extractor: JavaExtractor = JavaExtractor()

    filename: str = str(list(CONFIG.pdf_dir.glob(f'{courier_id}*.pdf'))[0])
    issue: ExtractedIssue =  extractor.extract_issue(filename)

    return issue

@dataclass(order=True, frozen=True)
class Page:
    page_number: int
    text: str

    def __post_init__(self) -> None:
        object.__setattr__(self, 'text', str(self.text))

    def __str__(self) -> str:
        return self.text


class Article:
    def __init__(self, index: dict, courier_issue: 'CourierIssue'):
        self.index = index
        self.courier_issue = courier_issue

    @property
    def pages(self) -> Iterator[Page]:
        for page_number in self.index['pages']:
            yield self.courier_issue.get_page(page_number)

    @property
    def courier_id(self) -> str:
        return self.index['courier_id']

    @property
    def record_number(self) -> str:
        return str(self.index['record_number'])

    @property
    def title(self) -> str:
        return self.index['catalogue_title']

    @property
    def year(self) -> str:
        return str(self.index['year'])


class CourierIssue:
    def __init__(self, courier_id: str):

        self.courier_id = courier_id

        if len(courier_id) != 6:
            raise ValueError(f'Not a valid courier id "{courier_id}')

        if courier_id not in CONFIG.article_index.courier_id.values:
            raise ValueError(f'{courier_id} not in article index')

        self.articles: List[Article] = self.get_articles()
        self.content: ExtractedIssue = get_pdf_issue_content(courier_id)

        self.drifted_double_pages = CONFIG.double_pages.get(courier_id, [])
        self.double_pages = [ x + i for i, x in enumerate(self.double_pages)]

    def get_article(self, record_number: str) -> Optional[Article]:
        return next((x for x in self.articles if x.record_number == record_number), None)

    def get_articles(self):
        articles: List[Article] = [ Article(x, self) for x in CONFIG.get_issue_article_index(self.courier_id) ]
        return articles

    @property
    def num_articles(self) -> int:
        return len(self.articles)

    @property
    def num_pages(self) -> int:
        return self.content.page_count

    # FIXME Hantera att endast första sidan av dubbelsidor returneras
    @property
    def pages(self) -> Iterator[Page]:
        for page in range(1, self.num_pages + 1):
            yield self.get_page(page)

    def get_page(self, page_number: int) -> Page:

        right_double_pages = [ x + i + 1 for i, x in enumerate(self.double_pages)]
        if page_number in right_double_pages:
            return None

        page_delta = len([x for x in self.double_pages if x < page_number])
        page = self.content.pages[page_number - page_delta]
        return Page(page_number, page)

    def page_numbers_mapping(self) -> Mapping[int, int]:
        total_pages = self.num_pages + len(self.double_pages)
        corrected_double_pages = [ x + i for i, x in enumerate(self.double_pages)]
        pages = [ x for x in range(1, total_pages + 1) if x - 1 in corrected_double_pages ]
        return pages

    def find_pattern(self, pattern: str) -> List[Tuple[int, int]]:
        page_numbers = []
        for i, page in enumerate(self.content.document.page, 1):
            m = re.search(pattern, page.cdata, re.IGNORECASE)
            if m:
                page_numbers.append((i, page['number']))
        return page_numbers


if __name__ == '__main__':
    pass
