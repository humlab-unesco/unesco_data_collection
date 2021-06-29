from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from courier.config import get_config
from courier.extract.cli import extract, get_extractor
from courier.extract.pdfbox_extractor import PDFBoxExtractor
from courier.extract.pdfminer_extractor import PDFMinerExtractor
from courier.extract.pdfplumber_extractor import PDFPlumberExtractor
from courier.extract.tesseract_extractor import TesseractExtractor

CONFIG = get_config()


@pytest.mark.java
@pytest.mark.parametrize(
    'method, instance',
    [
        ('PDFBox', PDFBoxExtractor),
        ('PDFMiner', PDFMinerExtractor),
        ('PDFPlumber', PDFPlumberExtractor),
        ('Tesseract', TesseractExtractor),
    ],
)
def test_get_extractor_returns_subclass_of_itextextractor(method, instance):
    extractor = get_extractor(method)
    assert isinstance(extractor, instance)


def test_get_extractor_with_unknown_method_raises_value_error():
    with pytest.raises(ValueError):
        get_extractor('Unknown method')


@pytest.mark.java
@pytest.mark.parametrize(
    'extractor, first_page, last_page, expected',
    [
        ('PDFBox', 1, None, 5),
        ('PDFBox', 2, 100, 3),
        ('PDFBox', 100, None, 0),
        ('PDFBoxHTML', 1, None, 5),
        ('PDFBoxHTML', 2, 100, 3),
        ('PDFBoxHTML', 100, None, 0),
        ('PDFMiner', 1, None, 5),
        ('PDFMiner', 2, 100, 3),
        ('PDFMiner', 100, None, 0),
        ('PDFPlumber', 1, None, 5),
        ('PDFPlumber', 2, 100, 3),
        ('PDFPlumber', 100, None, 0),
        ('Tesseract', 1, None, 5),  # FIXME: Patch tesseract settings
        ('Tesseract', 2, 100, 3),
        ('Tesseract', 100, None, 0),
    ],
)
def test_extract(extractor, first_page, last_page, expected):
    with TemporaryDirectory() as output_dir:
        extract(
            Path(CONFIG.test_files_dir / 'pdf'),
            output_dir,
            first_page=first_page,
            last_page=last_page,
            extractor=extractor,
        )
        result = len(sorted(Path(output_dir).glob('*.txt')))
        assert result == expected
        assert (Path(output_dir) / 'extract.log').exists()


@pytest.mark.java
@pytest.mark.parametrize(
    'extractor, first_page, last_page, expected',
    [
        ('PDFBox', 1, None, 2),
        ('PDFBoxHTML', 1, None, 2),
        ('PDFMiner', 1, None, 2),
        ('PDFPlumber', 1, None, 2),
        ('Tesseract', 1, None, 2),  # FIXME: Patch tesseract settings
    ],
)
def test_extract_with_logfile_partially_completed_jobs(extractor, first_page, last_page, expected):
    with TemporaryDirectory() as output_dir:
        with open(Path(output_dir) / 'extract.log', 'w') as fp:
            fp.write('2021-05-03 12:00:00.776 | SUCCESS | Extracted: 3_pages, pages: 3')
        assert (Path(output_dir) / 'extract.log').exists()
        extract(
            Path(CONFIG.test_files_dir / 'pdf'),
            output_dir,
            first_page=first_page,
            last_page=last_page,
            extractor=extractor,
        )
        result = len(sorted(Path(output_dir).glob('*.txt')))
        assert result == expected


@pytest.mark.java
@pytest.mark.parametrize(
    'extractor, first_page, last_page, expected',
    [
        ('PDFBox', 1, None, 0),
        ('PDFBoxHTML', 1, None, 0),
        ('PDFMiner', 1, None, 0),
        ('PDFPlumber', 1, None, 0),
        ('Tesseract', 1, None, 0),  # FIXME: Patch tesseract settings
    ],
)
def test_extract_with_logfile_fully_completed_jobs(extractor, first_page, last_page, expected):
    with TemporaryDirectory() as output_dir:
        with open(Path(output_dir) / 'extract.log', 'w') as fp:
            fp.writelines(
                [
                    '2021-05-03 12:00:00.776 | SUCCESS | Extracted: 3_pages, pages: 3\n',
                    '2021-05-03 12:00:00.130 | SUCCESS | Extracted: 2_pages_1_empty, pages: 2',
                ]
            )
        assert (Path(output_dir) / 'extract.log').exists()
        extract(
            Path(CONFIG.test_files_dir / 'pdf'),
            output_dir,
            first_page=first_page,
            last_page=last_page,
            extractor=extractor,
        )
        result = len(sorted(Path(output_dir).glob('*.txt')))
        assert result == expected
