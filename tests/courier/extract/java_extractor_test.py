from courier.config import get_config
from courier.extract.java_extractor import ExtractedIssue, JavaExtractor

CONFIG = get_config()


# TODO: Verify that titles are on correct pages!


def test_java_extractor():
    extractor: JavaExtractor = JavaExtractor()
    filename = CONFIG.pdf_dir / '012656engo.pdf'
    # filename: str = str(CONFIG.test_files_dir / 'test.pdf')
    # expected_output = CONFIG.test_files_dir / 'test.txt'

    issue: ExtractedIssue = extractor.extract_issue(filename)
    assert issue is not None
