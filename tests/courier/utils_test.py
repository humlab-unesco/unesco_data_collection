import sys

import pytest

from courier.config import get_config
from courier.utils import cdata, flatten, get_courier_ids, get_illegal_chars, pdf_stats

CONFIG = get_config()


def test_flatten_returns_expected_values():
    assert flatten([[1, 2, 3], (4, 5, 6), [7, 8]]) == [1, 2, 3, 4, 5, 6, 7, 8]
    assert flatten((('a', 'b'), [1, 2])) == ['a', 'b', 1, 2]


def test_pdf_stats(monkeypatch):
    monkeypatch.setattr(CONFIG, 'pdf_dir', CONFIG.test_files_dir)
    stats = pdf_stats()
    assert stats['files'] == 1
    assert stats['mean'] == 8
    assert stats['median'] == 8
    assert stats['pages'] == 8


@pytest.mark.parametrize(
    'maxunicode, expected',
    [
        (
            1114111,
            '[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x84\x86-\x9f\ufdd0-\ufddf\ufffe-\uffff\U0001fffe-\U0001ffff\U0002fffe-\U0002ffff\U0003fffe-\U0003ffff\U0004fffe-\U0004ffff\U0005fffe-\U0005ffff\U0006fffe-\U0006ffff\U0007fffe-\U0007ffff\U0008fffe-\U0008ffff\U0009fffe-\U0009ffff\U000afffe-\U000affff\U000bfffe-\U000bffff\U000cfffe-\U000cffff\U000dfffe-\U000dffff\U000efffe-\U000effff\U000ffffe-\U000fffff\U0010fffe-\U0010ffff]',
        ),
        (
            65535,
            '[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x84\x86-\x9f\ufdd0-\ufddf\ufffe-\uffff]',
        ),
    ],
)
def test_get_illegal_chars_returns_expected_for_wide_and_narrow_build(maxunicode, expected, monkeypatch):
    monkeypatch.setattr(sys, 'maxunicode', maxunicode)
    result = get_illegal_chars().pattern
    assert result == expected


def test_cdata_returns_expected():
    assert cdata('text') == '<![CDATA[\ntext\n]]>'


def test_cdata_nests_unallowed_string():
    assert cdata(']]>') == '<![CDATA[\n]]]]><![CDATA[>\n]]>'


def test_get_courier_ids_returns_list_of_basenames():
    assert all(isinstance(s, str) for s in get_courier_ids())
    assert all('.' not in s for s in get_courier_ids())
