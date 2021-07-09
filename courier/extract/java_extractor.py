# pyright: reportMissingImports=false
# pylint: disable=import-error, wrong-import-position

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Union

import jpype
import jpype.imports
from appdirs import AppDirs

from courier.config import get_config

CONFIG = get_config()

# FIXME: Cleanup
# pdfcourier2text_path = CONFIG.project_root / 'courier/lib/pdfbox-app-3.0.0-SNAPSHOT.jar'
cache_dir = Path(AppDirs('python-pdfbox').user_cache_dir)
pdfbox_path = list(cache_dir.glob('pdfbox-app-*.jar'))[-1]
pdfcourier2text_path = CONFIG.project_root / 'courier/lib/pdfextract-1.0-SNAPSHOT.jar'

# FIXME: Move to JavaExtractor class, add java args as option, add class paths at appropriate places, rename alias in 'import as'
if not jpype.isJVMStarted():
    jpype.addClassPath(pdfbox_path)
    jpype.addClassPath(pdfcourier2text_path)
    # jpype.startJVM(convertStrings=False)
    jpype.startJVM('-Dorg.apache.commons.logging.Log=org.apache.commons.logging.impl.NoOpLog', convertStrings=False)
# import org.apache.pdfbox.tools as pdfbox_tools  # isort: skip  # noqa: E402
import se.umu.humlab.pdfextract as pdfbox_tools  # isort: skip  # noqa: E402


@dataclass
class ExtractedPage:
    pdf_page_number: int
    content: str
    titles: List[Tuple[str, int]]


@dataclass
class ExtractedIssue:
    """Container for extracted raw text, and titles (text and positiopn) for a single issue.

    Note:
      - Page numbers are not corrected for double-pages (represented as a single image in PDF).
    """

    pages: List[ExtractedPage]

    def __len__(self) -> int:
        return len(self.pages or [])

    def __str__(self) -> str:
        return '\n\n'.join([str(p.content) for p in self.pages])


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
