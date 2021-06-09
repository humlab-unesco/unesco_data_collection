import functools
import operator
import re
import sys
from pathlib import Path
from statistics import median
from typing import Any, Dict, Iterable, Iterator, List

import pdf2image

from courier.config import get_config

CONFIG = get_config()


def flatten(list_of_list: Iterable[Iterable[Any]]) -> List[Any]:
    return functools.reduce(operator.iconcat, list_of_list, [])


def pdf_stats() -> Dict[str, int]:
    tot_pages = []
    for file in Path(CONFIG.pdf_dir).glob('*.pdf'):
        tot_pages.append(pdf2image.pdfinfo_from_path(file)['Pages'])
    return {
        'files': len(tot_pages),
        'pages': sum(tot_pages),
        'mean': round(sum(tot_pages) / len(tot_pages)),
        'median': round(median(tot_pages)),
    }


def get_illegal_chars() -> re.Pattern:
    """See: https://stackoverflow.com/a/64570125"""

    illegal_unichrs = [
        (0x00, 0x08),
        (0x0B, 0x0C),
        (0x0E, 0x1F),
        (0x7F, 0x84),
        (0x86, 0x9F),
        (0xFDD0, 0xFDDF),
        (0xFFFE, 0xFFFF),
    ]
    if sys.maxunicode >= 0x10000:
        illegal_unichrs.extend(
            [
                (0x1FFFE, 0x1FFFF),
                (0x2FFFE, 0x2FFFF),
                (0x3FFFE, 0x3FFFF),
                (0x4FFFE, 0x4FFFF),
                (0x5FFFE, 0x5FFFF),
                (0x6FFFE, 0x6FFFF),
                (0x7FFFE, 0x7FFFF),
                (0x8FFFE, 0x8FFFF),
                (0x9FFFE, 0x9FFFF),
                (0xAFFFE, 0xAFFFF),
                (0xBFFFE, 0xBFFFF),
                (0xCFFFE, 0xCFFFF),
                (0xDFFFE, 0xDFFFF),
                (0xEFFFE, 0xEFFFF),
                (0xFFFFE, 0xFFFFF),
                (0x10FFFE, 0x10FFFF),
            ]
        )

    illegal_ranges = [fr'{chr(l)}-{chr(h)}' for (l, h) in illegal_unichrs]
    xml_illegal_character_regex = '[' + ''.join(illegal_ranges) + ']'
    return re.compile(xml_illegal_character_regex)


ILLEGAL_CHARS = get_illegal_chars()


def valid_xml(value: str) -> str:
    return ILLEGAL_CHARS.sub('', value)


def cdata(value: str) -> str:
    value = value.replace(']]>', ']]]]><![CDATA[>')
    return f'<![CDATA[\n{value}\n]]>'


def get_courier_ids() -> List[str]:
    issues = sorted(list(Path(CONFIG.pdf_dir).glob('*.pdf')))
    return [x.stem for x in issues]


def split_by_idx(S: str, list_of_indices: List[int]) -> Iterator[str]:
    """See: https://stackoverflow.com/a/57342460"""
    left, right = 0, list_of_indices[0]
    yield S[left:right]
    left = right
    for right in list_of_indices[1:]:
        yield S[left:right]
        left = right
    yield S[left:]


if __name__ == '__main__':
    pass
