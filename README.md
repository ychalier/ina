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
python ina.py <action> [options]
```

Try using `python ina.py` to show help.

## Contributing

Contributions are welcomed. Push your branch and create a pull request detailling your changes.

## License

This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.
