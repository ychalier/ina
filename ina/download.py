"""Download module"""


import logging
import subprocess
import os
import eyed3
from ina.database import load_database
from ina.tools import tracked_loop


def download_video_id(options, entry, video_id):
    """Download a YouTube video, and check if it is the correct one"""
    url = "http://www.youtube.com/watch?v=" + video_id["video_id"]
    if video_id["title_error"] > options["title-error-threshold"]\
            or video_id["duration_error"] > options["duration-error-threshold"]:
        logging.warning("Media %s for %s might be incorrect", url, entry)
    command = [
        "youtube-dl",
        "--extract-audio",
        "--audio-format", "mp3",
        "--output", entry.filename() + ".%(ext)s",
        url
    ]
    with open(os.devnull, 'w') as devnull:
        process = subprocess.Popen(command, stdout=devnull)
    process.wait()


def set_tags(entry, video_id):
    """Set the ID3 tags of an entry"""
    filename = entry.filename() + ".mp3"
    audiofile = eyed3.load(filename)
    audiofile.initTag()
    url = "http://www.youtube.com/watch?v=" + video_id
    manual = 0
    if entry.credits.author is None:
        logging.error("File at %s has no artist", filename)
        manual += 2
    else:
        audiofile.tag.artist = entry.credits.author
    if entry.credits.director is None:
        logging.error("File at %s has no album artist", filename)
        manual += 4
    else:
        audiofile.tag.album_artist = entry.credits.director
    audiofile.tag.album = entry.category.collection_title
    audiofile.tag.title = entry.title
    audiofile.tag.track_num = entry.category.track_number, entry.category.track_total
    audiofile.tag.track_number = entry.category.track_number
    audiofile.tag.disc_num = 1, 1
    audiofile.tag.comments.set("Downloaded with InaRipper.")
    audiofile.tag.original_release_date = str(entry.diffusion.datetime)
    audiofile.tag.release_date = str(entry.diffusion.datetime)
    audiofile.tag.recording_date = str(entry.diffusion.datetime)
    audiofile.tag.audio_file_url = url.encode("utf8")
    audiofile.tag.genre = "Podcast"
    audiofile.tag.save()
    return manual


def download(options):
    """Download and set tags for all videos within selected collections"""
    database = load_database(options)
    collection_filters = set(database)
    if len(options["filter-collections"]) > 0:
        collection_filters = options["filter-collections"]
    for slug in collection_filters:
        logging.info("Downloading collection %s", slug)
        downloaded, existing, skipped = 0, 0, 0
        for entry in tracked_loop(
                database[slug],
                total=len(database[slug]),
                titler=lambda e: "Downloading %s" % e):
            filename = entry.filename()
            if os.path.isfile(filename + ".mp3"):
                logging.warning("%s already exists", entry)
                existing += 1
                continue
            entry.media.video_ids.sort(
                key=lambda d: (d["title_error"], d["duration_error"])
            )
            if len(entry.media.video_ids) == 0:
                logging.error("Could not download %s", entry)
                skipped += 1
                continue
            downloaded += 1
            download_video_id(options, entry, entry.media.video_ids[0])
            set_tags(entry, entry.media.video_ids[0]["video_id"])
    logging.info(
        "Dowloaded %d entries and skipped %d (%d already existed)",
        downloaded,
        skipped,
        existing
    )
