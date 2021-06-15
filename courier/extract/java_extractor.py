# pyright: reportMissingImports=false
# pylint: disable=import-error, wrong-import-position

import os
from dataclasses import dataclass
from typing import List, Tuple, Union

import jpype
import jpype.imports

from courier.config import get_config

CONFIG = get_config()
pdfcourier2text_path = CONFIG.project_root / 'courier/lib/pdfbox-app-3.0.0-SNAPSHOT.jar'

jpype.addClassPath(pdfcourier2text_path)
if not jpype.isJVMStarted():
    # jpype.startJVM(convertStrings=False)
    jpype.startJVM('-Dorg.apache.commons.logging.Log=org.apache.commons.logging.impl.NoOpLog', convertStrings=False)
import org.apache.pdfbox.tools as pdfbox_tools  # isort: skip  # noqa: E402


@dataclass
class ExtractedPage:
    pdf_page_number: int
    content: str
    # NOTE: titles optional?
    titles: List[Tuple[str, int]]


@dataclass
class ExtractedIssue:
    """Container for extracted raw text, and titles (text and positiopn) for a single issue.

    Note:
      - Page numbers are not corrected for double-pages (represented as a single image in PDF).
    """

    pages: List[ExtractedPage]

    # TODO: override __len__ instead?
    @property
    def page_count(self) -> int:
        return len(self.pages or [])


# TODO: Use this in `pdfbox_extractor` or new `custom_pdfbox_extractor`
# TODO: Add parameters `titleFontSizeInPt`, `minTitleLengthInCharacters`
class JavaExtractor:
    def __init__(self) -> None:
        self.extractor = pdfbox_tools.PDFCourier2Text(5.5, 8)

    def extract_issue(self, filename: Union[str, os.PathLike]) -> ExtractedIssue:
        filename = str(filename)
        pages = []
        for pdf_page_number, content in enumerate(self.extractor.extractText(filename), start=1):
            titles = [
                [(str(y.title), int(y.position)) for y in x] for x in self.extractor.getTitles()
            ]  # pylint: disable=W0631
            page: ExtractedPage = ExtractedPage(
                pdf_page_number=pdf_page_number,
                content=content,
                titles=titles[pdf_page_number - 1],
            )
            pages.append(page)

        issue: ExtractedIssue = ExtractedIssue(pages=pages)
        return issue


# java_extractor = JavaExtractor()
# content = java_extractor.extract_texts(str(CONFIG.pdf_dir / '012656engo.pdf'))
# # print(content[5])
# with open(CONFIG.project_root / 'tests/output/java_extractor_tmp.txt', 'w') as fp:
#     for i, x in enumerate(content, start=1):
#         fp.write(f'---------- Page {i} ----------\n{x}\n')
# len(content)
