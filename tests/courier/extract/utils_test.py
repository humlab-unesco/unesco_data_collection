from courier.extract.utils import get_filenames


def test_get_filenames_returns_only_files_with_expected_extension(tmp_path):

    pdf_file = tmp_path / 'test.pdf'
    pdf_file.touch()
    txt_file = tmp_path / 'test.txt'
    txt_file.touch()

    assert pdf_file in get_filenames(tmp_path)
    assert txt_file not in get_filenames(tmp_path)
    assert txt_file in get_filenames(tmp_path, 'txt')

    assert get_filenames(txt_file) == []
    assert get_filenames(pdf_file) == get_filenames(tmp_path) == [pdf_file]
