import io
import os
import re
from dataclasses import dataclass
from typing import List, Mapping, Optional, Set, Tuple, Union

import untangle

from courier.config import get_config
from courier.extract.java_extractor import ExtractedIssue, JavaExtractor
from courier.utils import split_by_idx, valid_xml

CONFIG = get_config()


def read_xml(filename: Union[str, bytes, os.PathLike]) -> untangle.Element:
    with open(filename, 'r') as fp:
        content = fp.read()
        content = valid_xml(content)
        xml = io.StringIO(content)
        element = untangle.parse(xml)
        return element


def get_pdf_issue_content(courier_id: str) -> ExtractedIssue:

    extractor: JavaExtractor = JavaExtractor()

    filename: str = str(list(CONFIG.pdf_dir.glob(f'{courier_id}*.pdf'))[0])
    issue: ExtractedIssue = extractor.extract_issue(filename)

    return issue


class Page:
    def __init__(self, page_number: int, text: str, titles: List[Tuple(str, int)], articles: List["Article"] = None):
        self.page_number: int = page_number
        self.text: str = str(text)
        self.titles: List[Tuple[str, int]] = titles
        self.articles: List['Article'] = articles or []

    def __str__(self) -> str:
        return self.text

    def segments(self) -> List[str]:
        if not self.titles:
            assert len(self.articles) == 1
            return [self.text]
        segments: List[str] = split_by_idx(
            self.text, [title_info[1] - len(title_info[0]) for title_info in self.titles]
        )
        # titled_text = ''.join(list(roundrobin(parts, [f'\n[___{title[0]}___]\n' for title in titles])))
        return segments


@dataclass(order=True, frozen=True)
class DoubleSpreadRightPage(Page):
    def __init__(self, page_number: int):
        super().__init__(page_number=page_number, text='', titles=[])


class Article:
    def __init__(
        self,
        courier_issue: 'CourierIssue',
        courier_id: str = None,
        year: str = None,
        record_number: str = None,
        pages: List[int] = None,
        catalogue_title: str = None,
    ):
        self.courier_issue = courier_issue
        self.courier_id: str = courier_id
        self.year: str = year
        self.record_number: str = record_number
        self.page_numbers: List[int] = pages  # TODO: Change name in article_index
        self.catalogue_title: str = catalogue_title
        self.pages: List[Page] = []
        self.texts: List[str] = []

    @property
    def min_page_number(self) -> int:
        return min(self.page_numbers)

    @property
    def max_page_number(self) -> int:
        return max(self.page_numbers)


# 069916;"10 11 24"
# def test_to_pdf_page_number() -> None:
#     issue = CourierIssue('012656')
#     assert 15 == issue.to_pdf_page_number(15)
#     assert 18 == issue.to_pdf_page_number(18)
#     assert 19 == issue.to_pdf_page_number(20)


class CourierIssue:
    def __init__(self, courier_id: str):

        self.courier_id = courier_id

        if len(courier_id) != 6:
            raise ValueError(f'Not a valid courier id "{courier_id}')

        if courier_id not in CONFIG.article_index.courier_id.values:
            raise ValueError(f'{courier_id} not in article index')

        self.articles: List[Article] = self._get_articles()
        self.content: ExtractedIssue = get_pdf_issue_content(courier_id)

        self._pdf_double_page_numbers: List[int] = CONFIG.double_pages.get(courier_id, [])

        self.double_pages: List[int] = [x + i for i, x in enumerate(self._pdf_double_page_numbers)]
        self.pages: List[Page] = PagesFactory().create(self)

    def to_pdf_page_number(self, page_number: int) -> int:
        _pdf_page_number = page_number - len([x for x in self.double_pages if x < page_number])
        return _pdf_page_number

    def get_article(self, record_number: str) -> Optional[Article]:
        return next((x for x in self.articles if x.record_number == record_number), None)

    def _get_articles(self) -> List[Article]:
        articles: List[Article] = [
            Article(courier_issue=self, **items) for items in CONFIG.get_issue_article_index(self.courier_id)
        ]
        return articles

    @property
    def num_articles(self) -> int:
        return len(self.articles)

    def __length__(self) -> int:
        return len(self.pages)

    def __get_item__(self, index: int) -> Page:
        return self.pages[index]

    def page_numbers_mapping(self) -> Mapping[int, int]:
        total_pages = len(self.pages) + len(self.double_pages)
        corrected_double_pages = [x + i for i, x in enumerate(self.double_pages)]
        pages = [x for x in range(1, total_pages + 1) if x - 1 in corrected_double_pages]
        return pages

    # def find_pattern(self, pattern: str) -> List[Tuple[int, int]]:
    #     page_numbers = []
    #     for i, page in enumerate(self.content.document.page, 1):
    #         m = re.search(pattern, page.cdata, re.IGNORECASE)
    #         if m:
    #             page_numbers.append((i, page['number']))
    #     return page_numbers


class PagesFactory:
    def create(self, issue: CourierIssue) -> CourierIssue:
        """Returns extracted page content"""
        num_pages = len(issue.content.pages) + len(issue.double_pages)

        pages = [
            DoubleSpreadRightPage(page_number)
            if page_number - 1 in issue.double_pages
            else Page(
                page_number=page_number,
                text=issue.content.pages[issue.to_pdf_page_number(page_number)].content,
                titles=issue.content.pages[
                    issue.to_pdf_page_number(page_number),
                ].titles,
            )
            for page_number in range(1, num_pages + 1)
        ]
        return pages


class AssignArticlesToPages:
    def assign(self, issue: CourierIssue) -> None:
        for page in issue.pages:
            if isinstance(page, DoubleSpreadRightPage):
                continue
            articles: List[Article] = self._find_articles_on_page(issue, page)
            page.articles = articles
            for article in articles:
                article.pages.append(page)

    def _find_articles_on_page(self, issue: CourierIssue, page: Page) -> List[Article]:

        articles = [a for a in issue.articles if page.page_number in a.page_number]

        return articles


class ConsolidateArticleTexts:
    def consolidate(self, issue: CourierIssue) -> CourierIssue:

        for article in issue.articles:
            for page in article.pages:

                if len(page.articles) == 1:
                    article.texts.append(page.text)
                elif len(page.articles) > 1:
                    text: str = self.extract_text(article, page)

    def extract_text(self, article: Article, page: Page):

        if len(page.articles) == 1:

            article.texts.append(page.text)

        elif len(page.articles) == 2:
            """Find break position and which part belongs to which article"""
            # Rule #1: If max(A1.page_number) == min(A2.page_numbers) ==> article A1 first on page
            # Rule #2: If min(A.page_number) == page then title is on page
            # A1 = [1,2,3]
            # A2 = [3,4,5]

            A1: Article = article
            A2: Article = page.articles[1] if page.articles[1] is not article else page.articles[0]

            if A1.min_page_number < page.page_number and A2.min_page_number == page.page_number:
                """A1 ligger först på sidan: => Hitta A2's titel"""
                position = self.find_matching_title_position(A2, page.titles)
                if position is not None:
                    A1.texts.append(page.text[:position])
            elif A2.min_page_number < page.page_number and A1.min_page_number == page.page_number:
                """A1 ligger sist på sidan: => Hitta A1's titel"""
                position = self.find_matching_title_position(A1, page.titles)
                if position is not None:
                    A1.texts.append(page.text[position:])

            # segments = page.segments()
            # text: str = self.extract_article_text(article, page)
            # page_titles = page.titles

    def find_matching_title_position(self, article: Article, titles: List) -> int:
        title_bow: Set[str] = set(article.catalogue_title.lower().split())
        for position, candidate_title in titles:
            candidate_title_bow: Set[str] = set(candidate_title.lower().split())
            common_words = title_bow.intersection(candidate_title_bow)
            if len(common_words) >= 2 and len(common_words) >= len(title_bow) / 2:
                return position


class ExtractArticles:
    def extract(issue: CourierIssue) -> CourierIssue:

        AssignArticlesToPages().assign(issue)
        ConsolidateArticleTexts().consolidate(issue)

        return issue


if __name__ == '__main__':
    import re

    issue = CourierIssue('012656')
    ExtractArticles().extract()
    for article in issue.articles:
        filename = os.path.join('/tmp', re.sub('[^-a-zA-Z0-9_.() ]+', '', article.catalogue_title.lower()))
        with open(filename, 'w') as fp:
            fp.write('\n\n'.join(article.texts))

# courier_id;year;record_number;pages;catalogue_title
# 074873;1974;50290;"[4, 5]";"1 + 1 = 3: every day over 200,000 more mouths to feed"
# 064696;1960;64362;"[6, 7]";"1,000 million lives in danger"
