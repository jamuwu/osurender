import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from itertools import count
import numpy as np
from osr import parse
import sys, time


def draw(path1, path2):
    start = time.time()
    fps = 30
    r1 = parse(path1)
    r2 = parse(path2)
    e1, e2 = r1.Events, r2.Events
    e1, e2 = r1.resample(fps), r2.resample(fps)

    fig, ax = plt.subplots()
    ax.axis('off')
    ax.set_xlim(0, 512)
    ax.set_ylim(0, 384)

    def update(i):
        t1 = e1.take(range(i - 5, i), 0)
        t2 = e2.take(range(i - 5, i), 0)
        p1 = ax.scatter([x[0] for x in t1], [x[1] for x in t1], 50, 'red')
        p2 = ax.scatter([x[0] for x in t2], [x[1] for x in t2], 50, 'blue')
        # Can't seem to figure out why legend won't work with two
        ax.legend((r1.username, r2.username))
        print(f'{i / max(len(e1), len(e2))*100:.2f}%', end='\r')
        return p1, p2

    ani = FuncAnimation(
        fig,
        update,
        frames=max(len(e1), len(e2)),
        interval=1000 / fps,
        blit=True)
    plt.show()
    #ani.save('test.mp4')
    print(f'\nFinished in {int(time.time() - start)} seconds.')

    return ani


if __name__ == '__main__':
    import os
    if len(sys.argv) < 3:
        print('Please provide two replays.')
        exit(0)
    path1 = sys.argv[1]
    path2 = sys.argv[2]
    if not os.path.exists(path1) or not os.path.exists(path2):
        print('Please provide two valid replays.')
        exit(0)

    draw(path1, path2)