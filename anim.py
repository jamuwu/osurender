import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from itertools import count
import numpy as np
from osr import parse
import sys, time


def draw(path):
    start = time.time()
    fps = 30
    r = parse(path)
    e = r.Events
    e = r.resample(fps)

    fig, ax = plt.subplots()
    ax.axis('off')
    ax.set_xlim(0, 512)
    ax.set_ylim(0, 384)

    def update(i):
        t = e.take(range(i - 5, i), 0)
        p = ax.scatter([x[0] for x in t], [x[1] for x in t], 50, 'red')
        ax.legend((r.username, ))
        print(f'{i / len(e) * 100:.2f}%', end='\r')
        return p,

    ani = FuncAnimation(
        fig, update, frames=len(e), interval=1000 / fps, blit=True)
    plt.show()
    #ani.save('test.mp4')
    print(f'\nFinished in {int(time.time() - start)} seconds.')

    return ani


if __name__ == '__main__':
    import os
    if len(sys.argv) < 2:
        print('Please provide a replay.')
        exit(0)
    path = sys.argv[1]
    if not os.path.exists(path):
        print('Please provide a valid replay.')
        exit(0)

    draw(path)