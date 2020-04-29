from PIL import Image, ImageDraw
import sys, time, imageio
from osr import Replay
import numpy as np

def render(path):
    start = time.time()
    r = Replay(path)

    video = imageio.get_writer(f'{r.username}-{r.timestamp}-{r.replayhash}.mp4', fps=60)

    for frame in r.frames:
        img = Image.new('RGBA', (552, 424), (0, 0, 0, 255))
        draw = ImageDraw.Draw(img)

        for event in frame:
            xy = (event[0] + 15, event[1] + 15, event[0] + 25, event[1] + 25)
            draw.ellipse(xy, fill=(0, 255, 205))

        video.append_data(np.array(img))

    print(f'\nFinished in {int(time.time() - start)} seconds.')

if __name__ == '__main__':
    import os
    if len(sys.argv) < 2:
        print('Please provide a replay.')
        exit(0)
    path = sys.argv[1]
    if not os.path.exists(path):
        print('Please provide a valid replay.')
        exit(0)

    render(path)