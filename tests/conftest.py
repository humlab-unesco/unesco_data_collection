# type: ignore
# noqa: F401,F811
# pyright: reportMissingImports=false, reportUnusedVariable=warning
# pylint: disable=unused-variable,unused-import,redefined-outer-name

import logging

import pytest
from _pytest.logging import caplog as _caplog
from loguru import logger


@pytest.fixture
def caplog(_caplog):
    """Captures `loguru` output so that it can be tested against
    See: https://loguru.readthedocs.io/en/stable/resources/migration.html#making-things-work-with-pytest-and-caplog
    """

    class PropogateHandler(logging.Handler):
        def emit(self, record):
            logging.getLogger(record.name).handle(record)

    handler_id = logger.add(PropogateHandler(), format='{message} {extra}')
    yield _caplog
    logger.remove(handler_id)
