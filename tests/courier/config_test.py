import csv
from pathlib import Path
from typing import Dict, List

import pytest

from courier.config import get_config, get_project_root

CONFIG = get_config()


def test_get_project_root_from_wrong_path_returns_path(monkeypatch):
    monkeypatch.setattr('os.getcwd', lambda: 'some/path')
    assert isinstance(get_project_root(), Path)


def test_config_paths_exists():
    for attr in dir(CONFIG):
        if isinstance(path := getattr(CONFIG, attr), Path):
            assert path.exists()


def test_pdfbox_xml_dir_contains_all_files():
    assert len(list(CONFIG.xml_dir.glob('*.xml'))) == 671


double_pages_testdata = [
    ('064331', [], [18]),
    ('069916', [], [10, 11, 24]),
    ('069916', [12], [10, 11, 24]),
    ('069916', None, [10, 11, 24]),
    ('110425', [], []),  # issues in exclusions
    ('000000', [], []),
    ('000000', [12], [12]),
    ('000000', None, None),
]


@pytest.mark.parametrize('courier_id,default_value,expected', double_pages_testdata)
def test_double_pages_returns_expected_values(courier_id, default_value, expected):
    result = CONFIG.double_pages.get(courier_id, default_value)
    assert result == expected


def test_double_pages_returns_empty_list_for_excluded_issue():

    with open(CONFIG.exclusions_file, newline='') as fp:
        reader = csv.reader(fp, delimiter=';')
        exclusions = [line[0] for line in reader]

    assert '110425' in exclusions
    assert CONFIG.double_pages.get('110425', []) == []


def test_get_issue_article_index():

    courier_id: str = '069916'
    index: List[Dict] = CONFIG.get_issue_article_index(courier_id)

    assert len(index) > 0


def test_get_courier_issue_index_return_expected_values():
    assert len(CONFIG.get_issue_article_index('061468')) == 3
