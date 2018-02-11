import sys
import os
import requests
import re
from tqdm import tqdm

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36"
FRAGMENT_PATTERN="video=(\d+),format="
FRAGMENT_REGEX= re.compile(FRAGMENT_PATTERN)
FRAGMENT_ARGS = "QualityLevels(3449984)/Fragments(video=%s,format=m3u8-aapl-v3,audiotrack=english)"
MANIFEST_ARGS = "QualityLevels(3449984)/Manifest(video,format=m3u8-aapl-v3,audiotrack=english,filter=hls)"


if __name__ == "__main__":
    link = sys.argv[2]

    if not link[:-1] == "/":
        link = link + "/"
    print(link)

    name = sys.argv[1]
    if not os.path.exists(name):
        os.makedirs(name)

    manifest_path = os.path.join(name, "manifest.txt")
    manifest_link = link + MANIFEST_ARGS
    print(manifest_link)
    
    response = requests.get(manifest_link,
                            headers={"User-Agent": USER_AGENT},
                            stream=True)
    with open(manifest_path, "wb") as f:
        for chunk in response:
            f.write(chunk)


    lines = ""
    with open(manifest_path, "r") as f:
        lines = f.read()

    numbers = re.findall(FRAGMENT_REGEX, lines)

    with open(os.path.join(name, "_files.txt"), 'w') as f:
        f.write("\n".join(["%s.frag" %(n) for n in numbers]))

    for n in tqdm(numbers):
        out_path = os.path.join(name, "%s.frag" %(n))
        response = requests.get(link + (FRAGMENT_ARGS % (n)),
                            headers={"User-Agent": USER_AGENT},
                            stream=True)
        with open(out_path, "wb") as f:
            for chunk in response:
                f.write(chunk)








