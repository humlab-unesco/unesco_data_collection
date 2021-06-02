# %%
# pyright: reportMissingImports=false
# pylint: disable=import-error, wrong-import-position
import os
from typing import Iterator, List, Tuple, Union

import jpype
import jpype.imports
from more_itertools import interleave_longest

from courier.config import get_config

CONFIG = get_config()
pdfcourier2text_path = CONFIG.project_root / 'courier/lib/pdfbox-app-3.0.0-SNAPSHOT.jar'

jpype.addClassPath(pdfcourier2text_path)
if not jpype.isJVMStarted():
    # jpype.startJVM(convertStrings=False)
    jpype.startJVM('-Dorg.apache.commons.logging.Log=org.apache.commons.logging.impl.NoOpLog', convertStrings=False)
import org.apache.pdfbox.tools as pdfbox_tools  # isort: skip  # noqa: E402


# %%

# https://stackoverflow.com/a/57342460
def split_by_idx(S: str, list_of_indices: List[int]) -> Iterator[str]:
    left, right = 0, list_of_indices[0]
    yield S[left:right]
    left = right
    for right in list_of_indices[1:]:
        yield S[left:right]
        left = right
    yield S[left:]


def insert_titles(page: str, titles: List[Tuple[str, int]]) -> str:
    if not titles:
        return page
    parts = split_by_idx(page, [title_info[1] - len(title_info[0]) for title_info in titles])
    titled_text = ''.join(list(interleave_longest(parts, [f'\n[_{title[0]}_]\n' for title in titles])))
    return titled_text


class JavaExtractor:
    def extract_texts(self, filename: Union[str, os.PathLike]) -> List[str]:
        extractor = pdfbox_tools.PDFCourier2Text(5.5, 8)
        pages = [str(page) for page in extractor.extractText(filename)]
        titles = [[(str(y.title), int(y.position)) for y in x] for x in extractor.getTitles()]

        text = [insert_titles(page, page_titles) for page, page_titles in zip(pages, titles)]
        return text


# %%
java_extractor = JavaExtractor()
content = java_extractor.extract_texts(str(CONFIG.pdf_dir / '012656engo.pdf'))
# %%

# for x in content:
#     print(x)
# jpype.shutdownJVM()

len(content)
print(content[5])

# %%