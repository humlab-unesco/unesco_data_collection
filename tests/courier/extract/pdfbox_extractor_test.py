import filecmp
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List

import pdfbox
import pytest

from courier.config import get_config
from courier.extract.interface import ITextExtractor
from courier.extract.pdfbox_extractor import PDFBoxExtractor
from courier.extract.utils import get_filenames

CONFIG = get_config()


@pytest.mark.java
def test_python_pdfbox_extract_text_generates_correct_output():

    file = CONFIG.test_files_dir / 'test.pdf'
    expected_output = CONFIG.test_files_dir / 'test.txt'
    p = pdfbox.PDFBox()

    with TemporaryDirectory() as output_dir:
        output_path = (Path(output_dir) / f'{file.stem}.txt').resolve()
        p.extract_text(file, output_path=output_path)

        assert output_path.exists()
        assert len(list(Path(output_dir).iterdir())) == 1
        assert filecmp.cmp(output_path, expected_output) is True


@pytest.mark.java
def test_extract_generates_expected_output():
    with TemporaryDirectory() as output_dir:
        files: List[Path] = get_filenames(CONFIG.test_files_dir / 'test.pdf')
        extractor: ITextExtractor = PDFBoxExtractor()
        extractor.batch_extract(files, output_dir)

        assert len(sorted(Path(output_dir).glob('*.txt'))) == 8
        assert (Path(output_dir) / 'extract.log').exists()
        assert filecmp.dircmp(output_dir, CONFIG.test_files_dir / 'expected/pdfbox').diff_files == []
        assert len(filecmp.dircmp(output_dir, CONFIG.test_files_dir / 'not_expected').diff_files) == 1
