# INA Ripper

This module extracts information from the [Inathèque](http://inatheque.ina.fr/)
database and provides tools to further locate those media on YouTube and
download them, along with setting the proper ID3 tags. Its purpose is made for
podcasts.

## Getting Started

### Prerequisites

Implementation uses Python 3 (v3.5.2. to be precise). It requires the following
executables:

 - [FFmpeg](https://www.ffmpeg.org/)
 - [youtube-dl](https://youtube-dl.org/)
 - a [Selenium](https://selenium-python.readthedocs.io/) driver such as [geckodriver](https://github.com/mozilla/geckodriver/releases)

Required python modules are in `requirements.txt`.

### Installing

Clone the repository, and make sure that `ffmpeg` and `youtube-dl` are in your path.

Then start the main script with:

```bash
python ina.py [action] [options]
```

### Demo

Here is a step-by step demo for downloading a series called [Les Maîtres du mystère](https://fr.wikipedia.org/wiki/Les_Maîtres_du_mystère).

1. **Scrap the database.** Use the action `scrap`, set the query with `-q` and, as we already now we are only looking for one collection, apply the adequate filter with `-c` to lighten database operations. The `-p` option makes sure that maximum 3 pages are requested, i.e. only 3*500 results maximum can be lookep up.

    ```
    python ina.py scrap -q "Les Maîtres du mystère" -c les-maitres-du-mystere -p 3
    ```

2. **Clean the database.** Remove duplicates, with action `clean`.

    ```
    python ina.py clean
    ```

3. **Enrich the database.** Fecth the author and the director of each entry, along with YouTube video ids candidates and add them to the database. This is done by the `enrich` action.

    ```
    python ina.py enrich -c les-maitres-du-mystere
    ```

4. **Manually select the correct video ids.** With action `select_media`. Warning triggering levels can be set with options `-t` (title error threshold, on a [0, 1] interval, measured as the [Jaccard index](https://en.wikipedia.org/wiki/Jaccard_index)) and `-u` (relative duration error threshold, on a [0, 1] interval). The maximum number of candidates showed to you can be changed with `-m`. Note that the first result is almomst always the best you can get browsing on [YouTube](https://www.youtube.com), however you can try to find it yourself and give it to the script if asked.

    ```
    python ina.py select_media -c les-maitres-du-mystere -u .05 -t .2 -m 3
    ```

5. **Download.** With action `download`. All corresponding collections will be downloaded using [youtube-dl](https://youtube-dl.org/) into [MP3](https://en.wikipedia.org/wiki/MP3) files, properly named, with [ID3](https://en.wikipedia.org/wiki/ID3) tags containing information gathered so far.

    ```
    python ina.py download -c les-maitres-du-mystere
    ```

6. **Cleanup the files.** There will be missing files, missing artist names, wrongly spelled album artist. To make up for that, use the additional script `unify` that takes a default album artist, an album cover (only [.jpg](https://en.wikipedia.org/wiki/JPEG)) and a folder as argumment, to clean all the audio files in that folder. Cleaning also involve shifting track ids so that no gap remains.

    ```
    python unify.py "Pierre Billard" ~/images/cover.jpg .
    ```

## Contributing

Contributions are welcomed. Push your branch and create a pull request detailling your changes.

## License

This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.
