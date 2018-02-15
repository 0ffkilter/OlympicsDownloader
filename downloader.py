#!/usr/bin/env python
import os, sys, requests, re, argparse, subprocess, shutil
import xml.etree.ElementTree as ET
from multiprocessing import Pool
from tqdm import tqdm
from html.parser import HTMLParser


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" + \
             "(KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36"
FRAGMENT_PATTERN = "video=(\d+),format="
FRAGMENT_REGEX = re.compile(FRAGMENT_PATTERN)
FRAGMENT_ARGS = "QualityLevels(3449984)/Fragments(video=%s," + \
                "format=m3u8-aapl-v3,audiotrack=english)"
MANIFEST_ARGS = "QualityLevels(3449984)/Manifest(video," + \
                "format=m3u8-aapl-v3,audiotrack=english,filter=hls)"
XML_FORMAT = "https://olympics.cbc.ca/videodata/%s.xml"


class CBCHTMLParser(HTMLParser):

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            if attrs[0][1] == "rc.idMedia":
                self.content_id = attrs[1][1]


def get_id(url):
    print("Getting video id:")
    parser = CBCHTMLParser()
    response = requests.get(url, headers={"User-Agent": USER_AGENT})
    parser.feed(response.text)
    print("\rGetting video id: %s" % (parser.content_id))
    return parser.content_id


def get_ism_link(content_id):
    print("Getting Manifest link")
    xml_link = XML_FORMAT % (content_id)
    response = requests.get(xml_link, headers={"User-Agent": USER_AGENT})
    tree = ET.fromstring(response.text)
    elt = tree.find("videoSources")
    for child in elt:
        if child.attrib["format"] == "HLS":
            print("\rGetting Manifest link: %s" % (child.find("uri").text))
            return child.find("uri").text


def fetch_file(url):
    if os.path.exists(url[0]):
        return
    response = requests.get(url[1],
                            headers={"User-Agent": USER_AGENT},
                            stream=True)
    with open(url[0], "wb") as f:
        for chunk in response:
            f.write(chunk)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", dest="dir", required=False, action="store",
                        metavar="path/", help="path to download directory")
    parser.add_argument("-i", dest="ism", required=False, action="store",
                        metavar="https://...",
                        help="URL of server manifest (.ism)")
    parser.add_argument("-o", dest="output", required=False, action="store",
                        metavar="out.mp4", help="output filename")
    parser.add_argument("-m", dest="manifest", required=False,
                        action="store", metavar="file", help=argparse.SUPPRESS)
    parser.add_argument("-t", dest="threads", required=False, action="store",
                        default=4, type=int, help="number of threads to use")
    parser.add_argument("--a", dest="aac_encoding", action="store_true",
                        required=False, help="use aac_adtstoasc encoding")
    parser.add_argument("--s", dest="save_parts", action="store_true",
                        required=False, help="save parts after stitching")
    parser.add_argument("-u", help="URL of video to download", required=False,
                        action="store", dest="url")

    options = parser.parse_args()

    if (not options.manifest and not options.url and not options.ism):
        print("Must supply an input")
        exit(1)

    #############
    # Directory #
    #############
    if options.dir:
        path = options.dir
    else:  # use download/
        path = "download/"
    if not os.path.exists(path):
        os.makedirs(path)

    ############
    # Manifest #
    ############
    if options.manifest:
        manifest_path = options.manifest
    elif options.url:
        manifest_link = get_ism_link(get_id(options.url))
        link = manifest_link[:manifest_link.find(".ism/") + 5]
        print("Downloading manifest")
        print(manifest_link)
        response = requests.get(link + MANIFEST_ARGS,
                                headers={"User-Agent": USER_AGENT},
                                stream=True)
        manifest_path = os.path.join(path, "_manifest.txt")
        with open(manifest_path, "wb") as f:
            for chunk in response:
                f.write(chunk)
    else:
        link = options.ism
        if link[-1] != "/":  # add a slash after the .ism
            link = link + "/"
        if link[-5:] != ".ism/":
            print("Manifest URL must end in .ism. Exiting.")
            exit(1)
        print("Downloading manifest")
        manifest_link = link + MANIFEST_ARGS
        response = requests.get(manifest_link,
                                headers={"User-Agent": USER_AGENT},
                                stream=True)
        manifest_path = os.path.join(path, "_manifest.txt")
        with open(manifest_path, "wb") as f:
            for chunk in response:
                f.write(chunk)

    lines = ""
    with open(manifest_path, "r") as f:
        lines = f.read()

    numbers = re.findall(FRAGMENT_REGEX, lines)

    with open(os.path.join(path, "_files.txt"), 'w') as f:
        f.write("\n".join(["file '{}.part'".format(n) for n in numbers]))

    #######################
    # Download fragments #
    ######################
    urls = []
    for n in numbers:
        out_path = os.path.join(path, "%s.part" % (n))
        urls.append((out_path, link + (FRAGMENT_ARGS % (n))))

    try:
        if options.threads > 1:
            with Pool(options.threads) as p:
                with tqdm(total=len(numbers)) as pbar:
                    for i, _ in tqdm(enumerate(
                                     p.imap_unordered(fetch_file, urls))):
                        pbar.update()
        elif options.threads == 1:
            for i, k in tqdm(urls):
                fetch_file((i, k))
    except KeyboardInterrupt:
        sys.exit(1)

    ##########
    # Concat #
    ##########
    filelist = os.path.join(path, "_files.txt")
    if options.output:
        filename = options.output
    else:
        filename = "out.mp4"
    subprocess.call(["ffmpeg", "-f", "concat", "-safe", "0", "-i",
                     filelist, "-c:v", "copy", "-c:a", "copy"] +
                    (["-bsf:a", "aac_adtstoasc"]
                     if options.aac_encoding else []) +
                    [filename])

    ###########
    # Cleanup #
    ###########
    if not options.save_parts:
        if options.dir:  # delete entire directory
            shutil.rmtree(path)
            os.rmdir(path)
        else:  # delete _files.txt and all .parts
            for item in os.listdir(path):
                if (item.endswith(".part") or
                    (item.startswith("_") and
                     item.endswith(".txt"))):
                    os.remove(os.path.join(path, item))
