""" INA Ripper (repository at https://github.com/ychalier/ina)"""


import logging
from ina.extraction import scrap, enrich
from ina.database import clean
from ina.download import download
from ina.database import select_media
from ina.factory import UnaryOption, BinaryOption, Factory


class InaRipper(Factory):
    """Factory extension for the INA Ripper"""

    def __init__(self):
        Factory.__init__(self, [
            BinaryOption("q", "query", ""),
            BinaryOption("c", "filter-collections", set(),
                         lambda x: set(x.split(" "))),
            BinaryOption("d", "database", "database.tsv"),
            UnaryOption("y", "skip-confirmation", False),
            BinaryOption("w", "delay", 1.5, float),
            BinaryOption("e", "driver-executable-path",
                         "/usr/local/bin/geckodriver"),
            UnaryOption("a", "append", False),
            BinaryOption("p", "max-page-requests", 300, int),
            BinaryOption("m", "max-media-candidates", 2, int),
            BinaryOption("t", "title-error-threshold", .5, float),
            BinaryOption("u", "duration-error-threshold", .05, float),
        ], {
            "scrap": scrap,
            "clean": clean,
            "enrich": enrich,
            "download": download,
            "select_media": select_media
        })


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s\t%(levelname)s\t%(message)s",
        level=logging.INFO
    )
    InaRipper().start()
