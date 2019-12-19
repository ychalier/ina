"""
Shift track ids, set the album cover and set a default album artist.

Usage:
    python unify.py [album_artist] [album_art] [folder]
"""


import os
import sys
import glob
import logging
import eyed3
from ina.tools import tracked_loop


def main():
    """Main module function"""
    logging.basicConfig(
        format="%(asctime)s\t%(levelname)s\t%(message)s",
        level=logging.INFO
    )
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit()
    album_artist, album_art, folder = sys.argv[1:]
    with open(album_art, "rb") as file:
        image = file.read()
    filenames = glob.glob(os.path.join(folder, "*.mp3"))
    filenames.sort()
    total = len(filenames)
    for i, filename in enumerate(tracked_loop(filenames, total, lambda s: s)):
        audiofile = eyed3.load(filename)
        if audiofile.tag.artist is None:
            audiofile.tag.artist = album_artist
        audiofile.tag.album_artist = album_artist
        audiofile.tag.track_num = i + 1, total
        audiofile.tag.track_number = total
        audiofile.tag.images.set(
            3,
            image,
            "image/jpeg",
            audiofile.tag.album
        )
        audiofile.tag.save()


if __name__ == "__main__":
    main()
