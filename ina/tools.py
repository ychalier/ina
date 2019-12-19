"""Tools for INA"""

import re
import time
import logging
import unicodedata


NON_URL_SAFE = ["\"", "#", "$", "%", "&", "+", ",", "/", ":", ";", "=", "?",
                "@", "[", "\\", "]", "^", "`", "{", "|", "}", "~", "'", "!"]

NON_URL_SAFE_REGEX = re.compile(r"[{}]".format(
    "".join(re.escape(x) for x in NON_URL_SAFE)))


def strip_accents(string):
    """Switch accented characters to normal characters in a string"""
    return "".join(
        char for char in unicodedata.normalize("NFD", string)
        if unicodedata.category(char) != "Mn"
    )


def slugify(string):
    """Return a unicode url-safe version of the input string"""
    return strip_accents("-".join(re.split(
        r"\s+",
        NON_URL_SAFE_REGEX.sub("", string.lower()).strip()
    )))


def timed_loop(iterator, delay):
    """Iterator wrapper that makes sure each loop is spaced in time"""
    for i in iterator:
        last_loop = time.time()
        yield i
        time_since_last_loop = time.time() - last_loop
        time_to_wait = max(0, delay - time_since_last_loop)
        time.sleep(time_to_wait)


STOPWORDS = set(["le", "la", "les", "l", "un", "une", "des"])


def tokenize(string):
    """Tokenize a string"""
    return set(slugify(string).split("-")).difference(STOPWORDS)


def jaccard(string_a, string_b):
    """Compute Jaccard distance between to strings"""
    tokens_a = tokenize(string_a)
    tokens_b = tokenize(string_b)
    return len(tokens_a.intersection(tokens_b)) / len(tokens_a.union(tokens_b))


def tracked_loop(iterator, total, titler):
    """Loops over an iterator and displays progress"""
    time_start = time.time()
    for i, value in enumerate(iterator):
        elapsed = time.time() - time_start
        if i == 0:
            eta = "--:--:--"
        else:
            eta = time.strftime(
                '%H:%M:%S',
                time.gmtime((total - i) * (elapsed / i))
            )
        logging.info(
            "[%s/%d | Elapsed: %s | ETA: %s] %s",
            "{number:0{width}d}".format(
                width=len(str(total)),
                number=i + 1
            ),
            total,
            time.strftime('%H:%M:%S', time.gmtime(elapsed)),
            eta,
            titler(value)
        )
        yield value
