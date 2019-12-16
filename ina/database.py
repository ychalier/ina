"""Database module"""

import datetime
import logging
import re
import os
import json
from functools import total_ordering
from ina.tools import slugify


class EntryParsingException(Exception):
    """Custom exception for entry parsing"""


class EntryDiffusion:
    """Diffusion information"""

    HEADER = ["diffusion_date", "diffusion_time", "diffusion_datetime", "diffusion_channel"]

    def __init__(self):
        self.date = None
        self.time = None
        self.channel = None
        self.datetime = None

    def serial(self, delimiter="\t"):
        """Serialize the object"""
        return delimiter.join(map(str, [self.date, self.time, self.datetime, self.channel]))

    def from_serial(self, split):
        """Recreates the object from its serialization"""
        self.date = split[0]
        self.time = split[1]
        self.channel = split[3]
        self.extract_datetime()

    def extract_datetime(self):
        """Set the datetime attribute from the date and the time ones"""
        if self.date == "":
            self.datetime = ""
        else:
            string = self.date + " " + self.time
            try:
                self.datetime = datetime.datetime.strptime(
                    string,
                    "%d/%m/%Y %H:%M:%S"
                )
            except ValueError:
                self.datetime = datetime.datetime.strptime(
                    self.date,
                    "%d/%m/%Y"
                )


class EntryCategory:
    """Categorisation information"""

    HEADER = ["collection", "collection_title", "track_number", "track_total", "program", "genre"]

    def __init__(self):
        self.collection = None
        self.collection_title = None
        self.track_number = None
        self.track_total = None
        self.program = None
        self.genre = None

    def serial(self, delimiter="\t"):
        """Serialize the object"""
        return delimiter.join(map(str, [
            self.collection,
            self.collection_title,
            self.track_number,
            self.track_total,
            self.program,
            self.genre
        ]))

    def from_serial(self, split):
        """Recreates the object from its serialization"""
        self.collection = split[0]
        self.collection_title = split[1]
        if split[2] != "None":
            self.track_number = int(split[2])
        if split[3] != "None":
            self.track_total = int(split[3])
        self.program = split[4]
        self.genre = split[5]


class EntryCredits:
    """Credits information"""

    HEADER = ["link", "text", "author", "director"]

    def __init__(self):
        self.link = None
        self.text = None
        self.author = None
        self.director = None

    def serial(self, delimiter="\t"):
        """Serialize the object"""
        return delimiter.join(map(str, [self.link, self.text, self.author, self.director]))

    def from_serial(self, split):
        """Recreates the object from its serialization"""
        self.link = split[0]
        self.text = split[1]
        self.extract_text()

    def extract_text(self):
        """Extract author and director from the html text"""
        search_results = re.findall("AUT,(.*?) ;", self.text)
        if len(search_results) > 0:
            self.author = " ".join(reversed(search_results[0].split(" ")))
        search_results = re.findall("REA,(.*?) ;", self.text)
        if len(search_results) > 0:
            self.director = " ".join(reversed(search_results[0].split(" ")))


class EntryMedia:
    """Entry media information"""

    HEADER = ["media"]

    def __init__(self):
        self.video_ids = list()

    def serial(self, delimiter="\t"):
        """Serialize the object"""
        return json.dumps(self.video_ids).replace(delimiter, "")

    def from_serial(self, split):
        """Recreates the object from its serialization"""
        if len("".join(split)) == 0:
            return
        self.video_ids = json.loads(split[0])

class EntryAttributes:
    """Entry attributes"""

    HEADER = ["duration_raw", "duration"]

    def __init__(self):
        self.duration_raw = None
        self.duration = None

    def serial(self, delimiter="\t"):
        """Serialize the object"""
        return delimiter.join(map(str, [self.duration_raw, self.duration]))

    def from_serial(self, split):
        """Recreates the object from its serialization"""
        self.duration_raw = split[0]
        self.duration = int(split[1])

    def extract_duration(self):
        """Extract the duration in seconds from the string field"""
        duration_str = self.duration_raw
        if len(duration_str) == 11:
            duration_str = duration_str[:-3]
        if len(duration_str) == 5:
            duration_str = "00:" + duration_str
        self.duration = 0
        for base, factor in zip([3600, 60, 1], duration_str.split(":")):
            self.duration += base * int(factor)


@total_ordering
class InaEntry:
    """Main entry representation object"""

    HEADER = "\t".join(
        ["title"]\
        + EntryCategory.HEADER\
        + EntryDiffusion.HEADER\
        + EntryCredits.HEADER\
        + EntryMedia.HEADER\
        + EntryAttributes.HEADER
    )

    def __init__(self):
        self.title = None
        self.category = EntryCategory()
        self.diffusion = EntryDiffusion()
        self.credits = EntryCredits()
        self.media = EntryMedia()
        self.attributes = EntryAttributes()

    def __hash__(self):
        return hash(slugify(self.title))

    def __eq__(self, other):
        return slugify(self.title) == slugify(other.title)\
            and self.category.collection_title == other.category.collection_title

    def __lt__(self, other):
        return self.diffusion.datetime < other.diffusion.datetime

    def serial(self, delimiter="\t"):
        """Serialize the object"""
        return delimiter.join(map(str, [
            self.title,
            self.category.serial(delimiter),
            self.diffusion.serial(delimiter),
            self.credits.serial(delimiter),
            self.media.serial(delimiter),
            self.attributes.serial(delimiter),
        ]))

    def from_serial(self, serial, delimiter="\t"):
        """Recreates the object from its serialization"""
        split = serial.split(delimiter)
        self.title = split[0]
        self.category.from_serial(split[1:7])
        self.diffusion.from_serial(split[7:11])
        self.credits.from_serial(split[11:15])
        self.media.from_serial(split[15:16])
        self.attributes.from_serial(split[16:18])

    def parse(self, row):
        """Extract entry information from search results row soup"""
        tds = list(map(lambda s: s.get_text().strip(), row.find_all("td")))
        if len(tds) != 9:
            raise EntryParsingException()
        self.diffusion.channel = tds[1]
        self.diffusion.date = tds[2]
        self.diffusion.time = tds[3]
        self.attributes.duration_raw = tds[4]
        self.title = tds[5]
        self.category.collection = tds[6]
        self.category.program = tds[7]
        self.category.genre = tds[8]
        link = row.find("a")
        if link is not None:
            self.credits.link = link["href"]

    def filename(self):
        """Return the filename for the downloaded entry"""
        return slugify("%s-%s-%s" % (
            self.category.collection_title,
            "{number:0{width}d}".format(
                width=len(str(self.category.track_total)),
                number=self.category.track_number
            ),
            self.title
        ))

def clean(options):
    """Clean action"""
    database = load_database(options)
    collection_titles = dict()
    for slug in database:
        for entry in database[slug]:
            collection_titles.setdefault(slug, dict())
            collection_titles[slug].setdefault(entry.category.collection, 0)
            collection_titles[slug][entry.category.collection] += 1
    collection_titles_map = {
        slug: sorted(titles.items(), key=lambda x: -x[1])[0][0]
        for slug, titles in collection_titles.items()
    }
    for slug in database:
        collection_title = collection_titles_map[slug]
        for entry in database[slug]:
            entry.category.collection_title = collection_title
        original_size = len(database[slug])
        database[slug] = list(set(database[slug]))
        new_size = len(database[slug])
        database[slug].sort()
        for i, entry in enumerate(database[slug]):
            entry.category.track_number = i + 1
            entry.category.track_total = new_size
        logging.info(
            "Collection '%s' has been cleaned, going from %d to %d entries (-%d)",
            slug,
            original_size,
            new_size,
            original_size - new_size
        )
    save_database(options, database)

def load_database(options):
    """Load an entry database"""
    logging.info("Loading database at %s", os.path.abspath(options["database"]))
    n_entries = 0
    database = dict()
    with open(options["database"], "r") as file:
        for entry_serial in file.readlines()[1:]:
            entry = InaEntry()
            entry.from_serial(entry_serial.strip())
            n_entries += 1
            slug = slugify(entry.category.collection)
            database.setdefault(slug, list())
            database[slug].append(entry)
    logging.info(
        "Loaded %d entries in the database, organized in %d collections",
        n_entries,
        len(database)
    )
    return database

def save_database(options, database):
    """Save an entry database"""
    logging.info("Saving database at %s", os.path.abspath(options["database"]))
    if not options["skip_confirmation"] and os.path.isfile(options["database"]):
        validation = input(
            "This action will reset the database at %s, continue? (y/n) "
            % os.path.abspath(options["database"])
        )
        if validation.lower() != "y":
            return
    i = 1
    with open(options["database"], "w") as file:
        file.write(InaEntry.HEADER + "\n")
        for slug in database:
            for entry in database[slug]:
                i += 1
                file.write(entry.serial() + "\n")
    logging.info("Wrote %d lines to %s", i, os.path.abspath(options["database"]))
