# cbc-olympics-dl

## Dependencies

* ffmpeg
* Python 2.7.x or 3.x
  * Packages: tqdm, requests

Requires a Canadian IP address.

## Usage

```
$ ./downloader.py [-d path/] -i "file.ism" [-o out.mp4]
```

`-d` is the path to an output directory. Defaults to `download/`.

`-i` is the URL of an .ism file (discoverable in chrome://net-internals > Events).

`-o` is the output filename. Defaults to output.mp4.

### Example usage

```
./downloader.py -d "temp/" -i "https://dvr-i-cbc.akamaized.net/.../4b5d.ism" -o "slopestyle.mp4"
```