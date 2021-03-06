# pylint: disable=redefined-outer-name

import io
import os
import re
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set, Tuple, Union

import ftfy
import untangle

from courier.config import get_config
from courier.extract.java_extractor import ExtractedIssue, ExtractedPage, JavaExtractor
from courier.utils import flatten, get_courier_ids, split_by_idx, valid_xml

CONFIG = get_config()


def read_xml(filename: Union[str, bytes, os.PathLike]) -> untangle.Element:
    with open(filename, 'r') as fp:
        content = fp.read()
        content = valid_xml(content)
        xml = io.StringIO(content)
        element = untangle.parse(xml)
        return element


# NOTE: Needed for test discovery (WIP). Remove later if deemed deprecated.
def get_xml_issue_content(courier_id: str) -> ExtractedIssue:

    if len(courier_id) != 6:
        raise ValueError(f'Not a valid courier id "{courier_id}')
    if courier_id not in CONFIG.article_index.courier_id.values:
        raise ValueError(f'{courier_id} not in article index')

    untangle_element = read_xml(list(CONFIG.xml_dir.glob(f'{courier_id}*.xml'))[0])
    pages = []
    for pdf_page_number, content in enumerate(untangle_element.document.page, 1):
        page: ExtractedPage = ExtractedPage(pdf_page_number=pdf_page_number, content=content, titles=[])
        pages.append(page)

    issue: ExtractedIssue = ExtractedIssue(pages=pages)
    return issue


def get_pdf_issue_content(courier_id: str) -> ExtractedIssue:
    extractor: JavaExtractor = JavaExtractor()
    filename: str = str(list(CONFIG.pdf_dir.glob(f'{courier_id}*.pdf'))[0])
    issue: ExtractedIssue = extractor.extract_issue(filename)
    return issue


class Page:
    def __init__(
        self,
        page_number: int,
        text: str,
        titles: Optional[List[Tuple[str, int]]] = None,
        articles: Optional[List['Article']] = None,
    ):
        self.page_number: int = page_number
        self.text: str = str(text)
        self.titles: List[Tuple[int, str]] = self.cleanup_titles(titles) if titles is not None else []
        self.articles: List['Article'] = articles or []

    def __str__(self) -> str:
        return self.text

    def cleanup_titles(self, titles: List[Tuple[str, int]]) -> List[Tuple[int, str]]:
        if titles is None:
            return []
        titles = [(position, ftfy.fix_text(title)) for title, position in titles]
        titles = [(position, ' '.join([x for x in title.split() if len(x) > 1])) for position, title in titles]
        return titles

    def get_pritty_titles(self) -> str:
        return f'{5*"-"}' + f'\n{5*"-"}'.join([f'\tposition {position}:\t"{title}"' for position, title in self.titles])

    def segments(self) -> List[str]:
        if not self.titles:
            assert len(self.articles) == 1
            return [self.text]
        segments: List[str] = list(split_by_idx(self.text, [position - len(title) for position, title in self.titles]))
        # titled_text = ''.join(list(roundrobin(parts, [f'\n[___{title[0]}___]\n' for title in titles])))
        return segments


@dataclass
class DoubleSpreadRightPage(Page):
    def __init__(self, page_number: int):
        super().__init__(page_number=page_number, text='', titles=None)


class Article:
    def __init__(
        self,
        courier_issue: 'CourierIssue',
        courier_id: Optional[str] = None,
        year: Optional[int] = None,
        record_number: Optional[int] = None,
        pages: Optional[List[int]] = None,
        catalogue_title: Optional[str] = None,
    ):
        self.courier_issue = courier_issue
        self.courier_id: Optional[str] = courier_id
        self.year: Optional[int] = year
        self.record_number: Optional[int] = record_number
        self.page_numbers: List[int] = pages or []  # TODO: Change name of pages in article_index page_numbers
        self.catalogue_title: str = catalogue_title or ''
        self.pages: List[Page] = []
        self.texts: List[Tuple[int, str]] = []
        self.errors: List[str] = []

    # FIXME: Check this
    @property
    def min_page_number(self) -> int:
        return 0 if self.page_numbers is None else min(self.page_numbers)

    # FIXME: Check this
    @property
    def max_page_number(self) -> int:
        return 0 if self.page_numbers is None else max(self.page_numbers)

    def get_text(self) -> str:
        text: str = ''
        text += f'{5*"-"} Title according to index: {self.catalogue_title}\n'
        text += f'{5*"-"} Pages according to index: {",".join(str(x) for x in self.page_numbers)}\n'
        text += f'{5*"-"} Assigned according to index: {self.page_numbers}\n'
        text += f'{5*"-"} Missing pages: {self.get_not_found_pages()}\n'
        text += f'{5*"-"}'.join(self.errors)
        for page_number, page_text in self.texts:
            text += f'\n{20*"-"} Page {page_number} {20*"-"}\n\n{page_text}\n'
        return text

    def get_assigned_pages(self) -> Set[int]:
        return {p[0] for p in self.texts}

    def get_not_found_pages(self) -> Set[int]:
        return {x for x in self.page_numbers if x not in self.get_assigned_pages()}


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
        _pdf_page_number = page_number - 1 - len([x for x in self.double_pages if x < page_number])
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

    def __len__(self) -> int:
        return len(self.pages)

    def __getitem__(self, index: int) -> Page:
        return self.pages[index]

    def get_page(self, page_number: int) -> Page:
        return self[page_number - 1]

    def get_assigned_pages(self) -> Set[int]:
        return {p.page_number for p in self.pages if len(p.articles) != 0}

    # TODO: Check
    def get_consolidated_pages(self) -> Set[int]:
        return set.union(*[p.get_assigned_pages() for p in self.articles])

    def get_article_pages(self) -> Set[int]:
        return set(flatten([a.page_numbers for a in self.articles]))

    # FIXME: Return correct item/type
    # def page_numbers_mapping(self) -> Mapping[int, int]:
    #     total_pages = len(self.pages) + len(self.double_pages)
    #     corrected_double_pages = [x + i for i, x in enumerate(self.double_pages)]
    #     pages = [x for x in range(1, total_pages + 1) if x - 1 in corrected_double_pages]
    #     return pages

    # def find_pattern(self, pattern: str) -> List[Tuple[int, int]]:
    #     page_numbers = []
    #     for i, page in enumerate(self.content.document.page, 1):
    #         m = re.search(pattern, page.cdata, re.IGNORECASE)
    #         if m:
    #             page_numbers.append((i, page['number']))
    #     return page_numbers


class PagesFactory:
    def create(self, issue: CourierIssue) -> List[Page]:
        """Returns extracted page content"""
        num_pages = len(issue.content.pages) + len(issue.double_pages)

        pages = [
            DoubleSpreadRightPage(page_number)
            if page_number - 1 in issue.double_pages
            else Page(
                page_number=page_number,
                text=issue.content.pages[issue.to_pdf_page_number(page_number)].content,
                titles=issue.content.pages[issue.to_pdf_page_number(page_number)].titles,
            )
            for page_number in range(1, num_pages + 1)
        ]
        return pages


class AssignArticlesToPages:
    def assign(self, issue: CourierIssue) -> None:
        if issue.get_assigned_pages():
            warnings.warn(f'Pages already assigned to {issue.courier_id}', stacklevel=2)
            return
        for page in issue.pages:
            if isinstance(page, DoubleSpreadRightPage):
                continue
            articles: List[Article] = self._find_articles_on_page(issue, page)
            page.articles = articles
            for article in articles:
                article.pages.append(page)

    def _find_articles_on_page(self, issue: CourierIssue, page: Page) -> List[Article]:
        articles = [
            a for a in issue.articles if page.page_number in a.page_numbers
        ]  # FIXME: Handle that a.page_numbers can be None
        return articles


class ConsolidateArticleTexts:
    def consolidate(self, issue: CourierIssue) -> None:
        for article in issue.articles:
            for page in article.pages:
                self.assign_segments_to_articles(article, page)

    def assign_segments_to_articles(self, article: Article, page: Page) -> None:
        if len(page.articles) == 1:
            article.texts.append((page.page_number, page.text))

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
                    A1.texts.append((page.page_number, page.text[:position]))
                else:
                    article.errors.append(
                        f'Unhandled case: Page {page.page_number}. Unable to find title on page (1st).'
                    )
                    article.errors.append(f'\nTitles on page {page.page_number}:\n{page.get_pritty_titles()}')

            elif A2.min_page_number < page.page_number and A1.min_page_number == page.page_number:
                """A1 ligger sist på sidan: => Hitta A1's titel"""
                position = self.find_matching_title_position(A1, page.titles)
                if position is not None:
                    A1.texts.append((page.page_number, page.text[position:]))
                else:
                    article.errors.append(
                        f'Unhandled case: Page {page.page_number}. Unable to find title on page (2nd).'
                    )
                    article.errors.append(f'\nTitles on page {page.page_number}:\n{page.get_pritty_titles()}')

            else:
                article.errors.append(f'Unhandled case: Page {page.page_number}. Two articles starting on same page.')

            # segments = page.segments()
            # text: str = self.extract_article_text(article, page)
            # page_titles = page.titles

        else:
            article.errors.append(f'Unhandled page {page.page_number}. More than two articles on page.')

    # NOTE: Main logic
    def find_matching_title_position(self, article: Article, titles: List) -> Optional[int]:
        if article.catalogue_title is None:
            return None
        title_bow: Set[str] = set(article.catalogue_title.lower().split())
        for position, candidate_title in titles:
            candidate_title_bow: Set[str] = set(candidate_title.lower().split())
            common_words = title_bow.intersection(candidate_title_bow)
            if len(common_words) >= 2 and len(common_words) >= len(title_bow) / 2:
                return position
        return None


@dataclass
class IssueStatistics:
    # all articles
    #   expected pages
    #   assigned pages
    # all pages
    issue: CourierIssue

    @property
    def total_pages(self) -> int:
        """Number of pages in issue"""
        return len(self.issue)

    @property
    def assigned_pages(self) -> int:
        """Number of pages in issue assigned to an article"""
        return len(self.issue.get_assigned_pages())

    @property
    def consolidated_pages(self) -> int:
        """Number of consolidated pages in issue"""
        return len(self.issue.get_consolidated_pages())

    @property
    def expected_article_pages(self) -> int:
        """Number of article pages in issue according to index"""
        return len(self.issue.get_article_pages())

    @property
    def number_of_articles(self) -> int:
        """Number of articles in issue"""
        return self.issue.num_articles


class ExtractArticles:
    @staticmethod
    def extract(issue: CourierIssue) -> CourierIssue:
        AssignArticlesToPages().assign(issue)
        ConsolidateArticleTexts().consolidate(issue)
        return issue

    @staticmethod
    def statistics(issue: CourierIssue) -> IssueStatistics:
        return IssueStatistics(issue)


# TODO: Add logging and skip completed. See extract.interface.ITextExtractor.batch_extract
def export_articles(
    courier_id: str,
    export_folder: Union[str, os.PathLike] = CONFIG.articles_dir / 'exported',
) -> None:

    issue = CourierIssue(courier_id)
    ExtractArticles.extract(issue)
    issue_statistics = ExtractArticles.statistics(issue)

    # TODO: Move to method in IssueStatistics
    print(
        f'Courier ID: {courier_id}. Total pages: {issue_statistics.total_pages}. Assigned {issue_statistics.assigned_pages} of {issue_statistics.expected_article_pages} pages ({100*issue_statistics.assigned_pages/issue_statistics.expected_article_pages:.2f}%)'
    )

    Path(export_folder).mkdir(parents=True, exist_ok=True)

    for article in issue.articles:
        if article.catalogue_title is None:
            continue
        safe_title = re.sub(r'[^\w]+', '_', str(article.catalogue_title).lower())
        file = Path(export_folder) / f'{article.courier_id}_{article.record_number}_{safe_title[:60]}.txt'
        with open(file, 'w') as fp:
            fp.write(article.get_text())


if __name__ == '__main__':
    courier_ids = [x[:6] for x in get_courier_ids()]
    for courier_id in courier_ids:
        if courier_id not in CONFIG.article_index.courier_id.values:
            print(f'{courier_id} not in article index')
            continue
        export_articles(courier_id)

    # export_articles('014255')
    # export_articles('015480')
    # export_articles('074873')
    # export_articles('098493')
