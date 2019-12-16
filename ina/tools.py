import re
import time
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