""" INA downloader

Usage:
    python ina.py (scrap|clean|enrich|download) [options]

Options:
    -q      query
    -cs     collection slugs filter
    -db     database file
    -y      skip confirmation
    -d      delay
"""


import logging
import sys
from ina.extraction import scrap, enrich
from ina.database import clean
from ina.download import download


def act(options, action):
    """Take actions"""
    if action == "scrap":
        scrap(options)
    elif action == "clean":
        clean(options)
    elif action == "enrich":
        enrich(options)
    elif action == "download":
        download(options)


def parse_arguments(args):
    """Parse input arguments and take corresponding actions"""
    if len(args) == 0:
        raise ValueError("Incorrect number of parameters")
    options = {
        "query": "Test",
        "collection_slugs": set(),
        "database": "database.tsv",
        "skip_confirmation": False,
        "delay": 1.5,
    }
    action = args[0]
    i = 1
    while i < len(args):
        if args[i] == "-q":
            options["query"] = args[i + 1]
            i += 2
        elif args[i] == "-cs":
            options["collection_slugs"] = set(args[i + 1].split(" "))
            i += 2
        elif args[i] == "-db":
            options["database"] = args[i + 1]
            i += 2
        elif args[i] == "-y":
            options["skip_confirmation"] = True
            i += 1
        else:
            logging.warning("Ignoring argument '%s'", args[i])
            i += 1
    for key, value in options.items():
        logging.info("Option '%s' is set to '%s'", key, value)
    if action not in ["scrap", "clean", "enrich", "download"]:
        raise ValueError("Incorrect action")
    return options, action


if __name__ == "__main__":
    LOG_FORMAT = "%(asctime)s\t%(levelname)s\t%(message)s"
    logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
    try:
        PARSED_ARGS = parse_arguments(sys.argv[1:])
    except ValueError as err:
        print(__doc__)
        sys.exit()
    act(*PARSED_ARGS)
