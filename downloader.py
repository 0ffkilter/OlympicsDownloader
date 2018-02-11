#!/usr/bin/env python

import sys, os, requests, re, argparse, subprocess, shutil
from tqdm import tqdm

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36"
FRAGMENT_PATTERN = "video=(\d+),format="
FRAGMENT_REGEX= re.compile(FRAGMENT_PATTERN)
FRAGMENT_ARGS = "QualityLevels(3449984)/Fragments(video=%s,format=m3u8-aapl-v3,audiotrack=english)"
MANIFEST_ARGS = "QualityLevels(3449984)/Manifest(video,format=m3u8-aapl-v3,audiotrack=english,filter=hls)"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", dest="dir", required=False, action="store", metavar="path/",
                        help="path to download directory")
    parser.add_argument("-i", dest="ism", required=True, action="store", metavar="https://...",
                        help="URL of server manifest (.ism)")
    parser.add_argument("-o", dest="output", required=False, action="store", metavar="out.mp4",
                        help="output filename")
    parser.add_argument("-m", dest="manifest", required=False, action="store", metavar="file",
                        help=argparse.SUPPRESS)
    options = parser.parse_args()

    #############
    # Directory #
    #############
    if options.dir:
        path = options.dir
    else: # use download/
        path = "download/"
    if not os.path.exists(path):
        os.makedirs(path)

    ############
    # Manifest #
    ############
    link = options.ism
    if link[-1] != "/": # add a slash after the .ism
        link = link + "/"
    if link[-5:] != ".ism/":
        print("Manifest URL must end in .ism. Exiting.")
        exit(1)

    if options.manifest:
        manifest_path = options.manifest
    else:
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
    for n in tqdm(numbers):
        out_path = os.path.join(path, "%s.part" %(n))
        response = requests.get(link + (FRAGMENT_ARGS % (n)),
                            headers={"User-Agent": USER_AGENT},
                            stream=True)
        with open(out_path, "wb") as f:
            for chunk in response:
                f.write(chunk)

    ##########
    # Concat #
    ##########
    filelist = os.path.join(path, "_files.txt")
    if options.output:
        filename = options.output
    else:
        filename = "out.mp4"
    subprocess.call(["ffmpeg", "-f", "concat", "-safe", "0", "-i", filelist, "-c:v", "copy", "-c:a", "copy", filename])

    ###########
    # Cleanup #
    ###########
    if options.dir: # delete entire directory
        shutil.rmtree(path)
    else: # delete _files.txt and all .parts
        for item in os.listdir(path):
            if item.endswith(".part") or (item.startswith("_") and item.endswith(".txt")):
                os.remove(os.path.join(path, item))
