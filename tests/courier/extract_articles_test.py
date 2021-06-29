from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from courier.config import get_config
from courier.elements import CourierIssue
from courier.extract_articles import extract_articles, extract_articles_from_issue

CONFIG = get_config()


def test_extract_article_as_xml():
    courier_issue = CourierIssue('061468')
    with TemporaryDirectory() as output_dir:
        extract_articles_from_issue(courier_issue, 'article.xml.jinja', output_dir)
        assert (Path(output_dir) / 'xml/061468_01_61469.xml').exists()


# TODO: Mock issue
@pytest.mark.skip(reason='Fix after update')
def test_extract_article_as_txt():
    courier_issue = CourierIssue('061468')
    with TemporaryDirectory() as output_dir:
        extract_articles_from_issue(courier_issue, 'article.txt.jinja', output_dir)
        assert len(list(Path(Path(output_dir) / 'txt').iterdir())) == 3

        article_1 = Path(output_dir) / 'txt/061468_01_61469.txt'
        article_2 = Path(output_dir) / 'txt/061468_02_61506.txt'
        article_3 = Path(output_dir) / 'txt/061468_03_61504.txt'

        assert article_1.exists()
        assert article_2.exists()
        assert article_3.exists()

        assert article_1.stat().st_size == 4968
        assert article_2.stat().st_size == 7500
        assert article_3.stat().st_size == 13973


@pytest.mark.parametrize(
    'courier_id, output_format, expected_num_articles',
    [
        ('012656', 'xml', 5),
        ('069916', 'txt', 8),
        ('061468', 'txt', 3),
    ],
)
def test_extract_articles_returns_expected_number_of_output_files(courier_id, output_format, expected_num_articles):

    assert CourierIssue(courier_id).num_articles == expected_num_articles

    with TemporaryDirectory() as output_dir:

        extract_articles(
            input_folder=CONFIG.test_files_dir / 'xml',
            template_name=f'article.{output_format}.jinja',
            output_folder=output_dir,
        )
        assert (
            len(list(Path(Path(output_dir) / output_format).glob(f'{courier_id}*.{output_format}')))
            == expected_num_articles
        )


def test_extract_articles_logging(tmp_path, caplog):

    test_file = tmp_path / '012656eng.xml'
    test_file.touch()
    duplicate = tmp_path / '012656engo.xml'
    duplicate.touch()

    # FIXME: 667? not 671
    total_files = len(CONFIG.article_index['courier_id'].unique())

    extract_articles(input_folder=tmp_path, output_folder=tmp_path)
    assert 'Duplicate matches for: 012656' in caplog.text
    assert 'No match' in caplog.text
    assert 'Missing courier_ids' in caplog.text

    assert len([msg for msg in caplog.messages if 'No match' in msg]) == total_files - 1
    assert len([msg for msg in caplog.messages if 'Duplicate matches' in msg]) == 1
    assert len([msg for msg in caplog.messages if 'Missing courier_ids' in msg]) == 1
