# pylint: disable=consider-using-with

from difflib import SequenceMatcher
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List

from courier.config import get_config
from courier.extract.interface import ITextExtractor
from courier.extract.pdfminer_extractor import PDFMinerExtractor
from courier.extract.utils import get_filenames

CONFIG = get_config()


def test_extract_generates_expected_output():
    with TemporaryDirectory() as output_dir:
        files: List[Path] = get_filenames(CONFIG.test_files_dir / 'test.pdf')
        extractor: ITextExtractor = PDFMinerExtractor()
        extractor.batch_extract(files, output_dir)

        num_extracted = len(sorted(Path(output_dir).glob('*.txt')))
        assert num_extracted == 8

        # FIXME: Improve
        for i in range(0, num_extracted):
            text1 = open(sorted(Path(output_dir).glob('*.txt'))[i]).read()
            text2 = open(sorted(Path(CONFIG.test_files_dir / 'expected/pdfminer').iterdir())[i]).read()
            m = SequenceMatcher(None, text1, text2)
            assert m.quick_ratio() > 0.99
