"""Download module"""


import logging
import subprocess
import time
import os
import eyed3
from ina.database import load_database


def download_video_id(options, entry, video_id):
    """Download a YouTube video, and check if it is the correct one"""
    filename = entry.filename()
    url = "http://www.youtube.com/watch?v=" + video_id["video_id"]
    if video_id["title_error"] > .5:
        logging.warning(
            "Media for %s has a weird title: '%s'",
            filename + ".mp3",
            video_id["title"],
        )
        if not (options["skip_confirmation"]
                or input("Is the media [%s] correct? (y/n) " % url).lower() == "y"):
            return False
    if video_id["duration_error"] > .05:
        logging.warning(
            "%s has a duration of %ds (%s) but we expected %ds (%s)",
            filename + ".mp3",
            video_id["duration"],
            time.strftime('%H:%M:%S', time.gmtime(video_id["duration"])),
            entry.attributes.duration,
            time.strftime('%H:%M:%S', time.gmtime(entry.attributes.duration)),
        )
        if not (options["skip_confirmation"]
                or input("Is the media [%s] correct? (y/n) " % url).lower() == "y"):
            return False
    command = [
        "youtube-dl",
        "--extract-audio",
        "--audio-format", "mp3",
        "--output", filename + ".%(ext)s",
        url
    ]
    with open(os.devnull, 'w') as devnull:
        process = subprocess.Popen(command, stdout=devnull)
    process.wait()
    return True


def download(options):
    """Download action"""
    database = load_database(options)
    collection_filters = set(database)
    if len(options["collection_slugs"]) > 0:
        collection_filters = options["collection_slugs"]
    for slug in collection_filters:
        logging.info("Downloading collection %s", slug)
        time_start = time.time()
        downloaded, skipped = 0, 0
        for i, entry in enumerate(database[slug]):
            filename = entry.filename()
            elapsed = time.time() - time_start
            if downloaded == 0:
                eta = "--:--:--"
            else:
                eta = (len(database[slug]) - i) * (elapsed / downloaded)
                eta = time.strftime('%H:%M:%S', time.gmtime(eta))
            logging.info(
                "[%s/%d | Elapsed: %s | ETA: %s] Downloading %s",
                "{number:0{width}d}".format(
                    width=len(str(len(database[slug]))),
                    number=i + 1
                ),
                len(database[slug]),
                time.strftime('%H:%M:%S', time.gmtime(elapsed)),
                eta,
                filename + ".mp3"
            )
            if os.path.isfile(filename + ".mp3"):
                skipped += 1
                continue
            entry.media.video_ids.sort(
                key=lambda d: (d["title_error"], d["duration_error"]))
            last_video_id = ""
            for video_id in entry.media.video_ids:
                last_video_id = video_id["video_id"]
                success = download_video_id(options, entry, video_id)
                if success:
                    break
            if os.path.isfile(filename + ".mp3"):
                set_tags(entry, last_video_id)
            else:
                logging.error("Could not download %s", filename + ".mp3")
            downloaded += 1
        logging.info(
            "Dowloaded %d entries and skipped %d",
            downloaded,
            skipped
        )


def set_tags(entry, last_video_id):
    """Set the ID3 tags of an entry"""
    audiofile = eyed3.load(entry.filename() + ".mp3")
    audiofile.initTag()
    url = "http://www.youtube.com/watch?v=" + last_video_id
    audiofile.tag.artist = entry.credits.author
    audiofile.tag.album = entry.category.collection_title
    audiofile.tag.album_artist = entry.credits.director
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
