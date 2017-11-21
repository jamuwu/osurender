#!/usr/bin/python3.5
# This script would probably be a lot better
# If it wasn't synchronous, if you know an
# Easy way for someone to learn to use
# Threads, please let me know :)
import pyttanko
from PIL import Image, ImageDraw
import os, sys, math, time

if len(sys.argv) < 2:
    sys.stderr.write("You need to provide a map to render!\n")
    sys.exit()
else: filename = sys.argv[1]

try:
    bmap = pyttanko.parser().map(open(filename))
    stars = pyttanko.diff_calc().calc(bmap)
except:
    sys.stderr.write("Sorry, pyttanko doesn't seem to like the file you gave!\n")
    sys.exit()

# found this on reddit
def cs_px(cs): return int(109 - 9 * cs)

# math from pyttanko without the variables
def ar_ms(ar):
    if ar < 5.0: arms = 1800 - 120 * ar
    else: arms = 1200 - 150 * (ar - 5)
    return int(arms)

# bezier code from https://stackoverflow.com/questions/246525/how-can-i-draw-a-bezier-curve-using-pythons-pil
# literally don't ask me because I have no idea what it's doing lmao
def make_bezier(xys):
    # xys should be a sequence of 2-tuples (Bezier control points)
    n = len(xys)
    combinations = pascal_row(n-1)
    def bezier(ts):
        # This uses the generalized formula for bezier curves
        # http://en.wikipedia.org/wiki/B%C3%A9zier_curve#Generalization
        result = []
        for t in ts:
            tpowers = (t**i for i in range(n))
            upowers = reversed([(1-t)**i for i in range(n)])
            coefs = [c*a*b for c, a, b in zip(combinations, tpowers, upowers)]
            result.append(
                tuple(sum([coef*p for coef, p in zip(coefs, ps)]) for ps in zip(*xys)))
        return result
    return bezier

def pascal_row(n):
    # This returns the nth row of Pascal's Triangle
    result = [1]
    x, numerator = 1, n
    for denominator in range(1, n//2+1):
        # print(numerator,denominator,x)
        x *= numerator
        x /= denominator
        result.append(x)
        numerator -= 1
    if n&1 == 0:
        # n is even
        result.extend(reversed(result[:-1]))
    else:
        result.extend(reversed(result)) 
    return result

def slider_end_time(obj):
    # Used to be highly innacurate when I tried doing this myself
    # Thanks to fmang for documenting how this is found.
    # I think it's implemented properly but still feel it's a tad bit off.
    # TODO test some more and find issues
    timings = bmap.timing_points
    for timing in timings:
        if obj.time >= timing.time:
            t = timing
            break
    return obj.data.distance / (100.0 * bmap.sv) * t.ms_per_beat # The actual 

def slider_curve(red): # I'll work on this later to make it actually work in producing true slider paths
    if   len(red) == 2: return red
    #elif len(red) == 3: return perfect(red) # TODO implement this
    else:
        bezier = make_bezier(red)
        return bezier(ts)

def circlecalc(obj, offset:int):
    # I didn't want to type this twice lol
    x1 = (obj.data.pos.x + 20) - offset
    x2 = (obj.data.pos.y + 20) - offset
    y1 = (obj.data.pos.x + 20) + offset
    y2 = (obj.data.pos.y + 20) + offset
    return (x1, x2, y1, y2)

def parsePoints(points): 
    # This doesn't look so good. TODO make this better/more efficient
    temp, temps = [], []
    for i in range(len(points)):
        temp.append(points[i])
        if i + 1 < len(points):
            if points[i] == points[i + 1]:
                temps.append(temp)
                temp = [points[i]]
        else: temps.append(temp)
    return temps

def createbuffer(i):
    # creates a new buffer containing only objects that are within the current time frame
    # slow, is there any way to do this faster?
    buffer = []
    for obj in bmap.hitobjects:
        # this *should* identify whether the object should be shown or not
        if obj.objtype & 1<<0 != 0: # Circle
            if i >= obj.time - arms and i <= obj.time:
                buffer.append(obj)
        elif obj.objtype & 1<<1 != 0: # Slider
            if i >= obj.time - arms and i <= obj.time + int(slider_end_time(obj)):
                buffer.append(obj)
        elif obj.objtype & 1<<3 != 0: # Spinner
            if i >= obj.time and i <= obj.endtime:
                buffer.append(obj)
    return buffer

dirname = '{} - {}'.format(bmap.title, bmap.version) # this is our working directory
if not dirname in os.listdir('.'): os.mkdir(dirname) # makes the directory if it doesn't exist
cspx = cs_px(bmap.cs)
arms = ar_ms(bmap.ar)
objectbuffer = [] # controlled by the checkbuffer function
ts = [t/100.0 for t in range(101)]

sys.stdout.write('{}[{}] by {}\n'.format(bmap.title, bmap.version, bmap.creator))
sys.stdout.write('CS: {}({}px) AR: {}({}ms)\n'.format(bmap.cs, cs_px(bmap.cs), bmap.ar, ar_ms(bmap.ar)))

start = time.perf_counter()
# Loops through the map generating a frame every 20ms
# Allowing us to gracefully make a 50fps video...
# For a 60fps video it'd be (1 / 60) / (1 / 100)
# You can probably work out why'd I'd rather stick
# To a clean number like 20 instead
for i in range(int((bmap.hitobjects[-1].time + 2000) / 20)):
    i = (i + 1) * 20
    frame = Image.new('RGBA', (552, 424), (0, 0, 0, 255))
    draw = ImageDraw.Draw(frame)
    buffer = createbuffer(i)
    for obj in buffer:
        if obj.objtype & 1<<0 != 0: # Circle
            draw.ellipse(circlecalc(obj, cspx / 2))
            draw.ellipse(circlecalc(obj, cspx / 2 + (cspx * .65)  * ((obj.time - i) / arms)))
        elif obj.objtype & 1<<1 != 0: # Slider
            draw.ellipse(circlecalc(obj, cspx / 2))
            draw.ellipse(circlecalc(obj, max(cspx / 2 + (cspx * .65)  * ((obj.time - i) / arms), cspx / 2)))
            points = [(obj.data.pos.x + 20, obj.data.pos.y + 20)]
            points.extend([(int(point.split(':')[0]) + 20, int(point.split(':')[1]) + 20) for point in obj.data.points.split('|') if ':' in point])
            segments, slider = parsePoints(points), []
            for red in segments:
                draw.line(slider_curve(red))
        elif obj.objtype & 1<<3 != 0: # Spinner
            x, y = 276, 212
            draw.ellipse((x - 100, y - 100, x + 100, y + 100))
    frame.save('{}/{}.png'.format(dirname, str(int(i / 20)).zfill(8)))
    sys.stdout.write('{:>7}/{} {:.2f}% done.\r'.format(int(i), int(bmap.hitobjects[-1].time + 2000), i / int(bmap.hitobjects[-1].time + 2000) * 100))

sys.stdout.write('Took {:.2f} seconds to finish.\n'.format(time.perf_counter() - start))

# Since I want to use PIL and have no idea how to make a video from images in python
# Would love to learn of a way that doesn't require installing things like opencv
# I'll use ffmpeg from command line for now, possibly for an indefinite amount of time.
# ffmpeg -r 50 -f image2 -i maptitle/%08d.png -i mapaudio.mp3 -vcodec libx264 -crf 25 -pix_fmt yuv420p video.mp4