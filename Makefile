SHELL := /bin/bash
SOURCE_FOLDERS=courier tests tmp
PACKAGE_FOLDER=courier
BLACK_ARGS=--line-length 120 --target-version py38 --skip-string-normalization -q
FLAKE8_ARGS=--extend-ignore=BLK100,E302,E303
MYPY_ARGS=--show-column-numbers --no-error-summary
ISORT_ARGS=--profile black --float-to-top --line-length 120 --py 38
#PYTEST_ARGS=--durations=0 --cov=$(PACKAGE_FOLDER) --cov-report=xml --cov-report=html tests
#PYTEST_ARGS=--cov=$(PACKAGE_FOLDER) --cov-report=xml --cov-report=html
PYTEST_ARGS=--cov=$(PACKAGE_FOLDER) --cov-report=xml --cov-report=html --cov-branch

tidy: isort black

lint: tidy pylint flake8 mypy

clean:
	@rm -rf .coverage coverage.xml htmlcov .nox
	@find . -type d -name '__pycache__' -exec rm -rf {} +
	@find . -type d -name '*pytest_cache*' -exec rm -rf {} +
	@find . -type d -name '.mypy_cache' -exec rm -rf {} +
	@rm -rf tests/output

test: clean
	@mkdir -p ./tests/output
	@poetry run pytest $(PYTEST_ARGS) tests
	@rm -rf ./tests/output/*

test_no_legacy: clean
	@mkdir -p ./tests/output
	@poetry run pytest -m "not legacy" $(PYTEST_ARGS) tests
	@rm -rf ./tests/output/*

pylint:
	@poetry run pylint --version | grep pylint
	@poetry run pylint $(SOURCE_FOLDERS)

.ONESHELL: pylint_diff
pylint_diff:
	@delta_files=$$(git status --porcelain | awk '{print $$2}' | grep -E '\.py$$' | tr '\n' ' ')
	@if [[ "$$delta_files" != "" ]]; then
		poetry run pylint --version | grep pylint
		poetry run pylint $$delta_files
	fi

notes:
	@poetry run pylint --version | grep pylint
	@poetry run pylint --notes=FIXME,XXX,TODO --disable=all --enable=W0511 -f colorized $(SOURCE_FOLDERS)

flake8:
	@poetry run flake8 --version
	@poetry run flake8 $(FLAKE8_ARGS) $(SOURCE_FOLDERS)

mypy:
	@poetry run mypy --version
	@poetry run mypy $(MYPY_ARGS) $(SOURCE_FOLDERS)

black:
	@poetry run black --version
	@poetry run black $(BLACK_ARGS) $(SOURCE_FOLDERS)

isort:
	@echo isort `poetry run isort --vn`
	@poetry run isort $(ISORT_ARGS) $(SOURCE_FOLDERS)

articles:
	@echo Etracting articles
	@poetry run python courier/extract_articles.py
	@poetry run python courier/extract_articles.py -t 'article.txt.jinja'

# pages_pbfbox:
# 	@echo Extracting pages
# 	@poetry run python courier/pdfbox_extract.py ~/data/courier/pdf/ ~/data/courier/pages/pdfbox 2>/dev/null

# pages_tesseract:
# 	@echo Extracting pages
# 	@poetry run python courier/tesseract_extract.py ~/data/courier/pdf/ ~/data/courier/pages/tesseract

PDFS = ~/data/courier/pdf
PAGES = ~/data/courier/pages
XML = ~/data/courier/xml

# extract_pages: extract_pages_pdfbox extract_pages_pdfminer extract_pages_pdfplumber

extract_pages_pdfbox:
	@poetry run python courier/extract/cli.py $(PDFS) $(PAGES)/pdfbox --extractor PDFBox 2>/dev/null

extract_pages_pdfminer:
	@poetry run python courier/extract/cli.py $(PDFS) $(PAGES)/pdfminer --extractor PDFMiner

extract_pages_pdfplumber:
	@poetry run python courier/extract/cli.py $(PDFS) $(PAGES)/pdfplumber --extractor PDFPlumber

extract_pages_tesseract:
	@poetry run python courier/extract/cli.py $(PDFS) $(PAGES)/tesseract --extractor Tesseract

.PHONY: extract_pages_pdfbox extract_pages_pdfminer extract_pages_pdfplumber extract_pages_tesseract

compile_issues_pdfbox:
	@poetry run python courier/compile_issues.py $(PAGES)/pdfbox $(XML)/pdfbox

compile_issues_pdfminer:
	@poetry run python courier/compile_issues.py $(PAGES)/pdfminer $(XML)/pdfminer

compile_issues_pdfplumber:
	@poetry run python courier/compile_issues.py $(PAGES)/pdfplumber $(XML)/pdfplumber

compile_issues_tesseract:
	@poetry run python courier/compile_issues.py $(PAGES)/tesseract $(XML)/tesseract

compile_issues: compile_issues_pdfbox compile_issues_pdfminer compile_issues_pdfplumber compile_issues_tesseract

.PHONY: compile_issues_pdfbox compile_issues_pdfminer compile_issues_pdfplumber compile_issues_tesseract compile_issues

# tools:
# 	@pip install --upgrade pip -q
# 	@pip install poetry --upgrade -q
# 	@poetry run pip install --upgrade pip -q

# NOTE: tools should not be run while in poetry shell
# .PHONY: tools

.PHONY: help
.PHONY: clean
.PHONY: test
.PHONY: lint pylint flake8 mypy pylint_diff notes
.PHONY: tidy black isort
.PHONY: articles

help:
	@echo "Higher level recepies: "
	@echo " make clean            Removes temporary files, caches, and build files"
	@echo " make lint             Runs tidy, pylint, flake8 and mypy"
	@echo " make test             Runs tests with code coverage"
	@echo " make tidy             Runs black and isort"
	@echo "  "
	@echo "Lower level recepies: "
	@echo " make black            Runs black"
	@echo " make flake8           Runs flake8"
	@echo " make isort            Runs isort"
	@echo " make mypy             Runs mypy"
	@echo " make notes            Runs pylint with notes"
	@echo " make pylint           Runs pylint"
	@echo " make pylint_diff      Runs pylint on changed files only"
	@echo "  "
	@echo "Extracting: "
	@echo " make articles         Extract artcles"
	@echo " make pages_pbfbox     Extract pages from PDF:s using PDFBox"
	@echo " make pages_tesseract  Extract pages from PDF:s using Tesseract"