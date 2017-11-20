#!/usr/bin/python3.5
# I really wanted to use pyttanko for this but
# I'm already too used to this
from parsers import parseReplay, parse_osu
from PIL import Image, ImageDraw
import os, sys, math, time
#from parsers import parse_osu

framems = (1 / 60) / (1 / 1000)

if len(sys.argv) < 2:
    sys.stderr.write("You need to provide a map to render!\n")
    sys.exit()
else: filename = sys.argv[1]

try:
    bmap = parse_osu(filename)
except:
    sys.stderr.write("Sorry, the parser doesn't seem to like the file you gave!\n")
    sys.exit()

def cs_px(cs): return 109 - 9 * cs

def ar_ms(ar):
    if ar < 5.0: arms = 1800 - 120 * ar
    else: arms = 1200 - 150 * (ar - 5)
    return arms

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

def scale_number(unscaled, to_min, to_max, from_min, from_max):
    return (to_max-to_min)*(unscaled-from_min)/(from_max-from_min)+to_min

def scale_list(l, to_min, to_max):
    return [scale_number(i, to_min, to_max, min(l), max(l)) for i in l]

def get_current_timing(i):
    timings = bmap[2]
    for timing in timings:
        if i.time >= timing.time:
            return timing

def slider_end_time(obj):
    currentSection = get_current_timing(obj)
    pxPerBeat = bmap[1]['slider_multiplier'] * 100 * currentSection.time
    beatsNumber = (obj.pixellength * obj.repeat) / pxPerBeat
    msLength = beatsNumber * currentSection.mpb
    return msLength * 100

def circlecalc(obj, offset:int):
    x1 = (obj.x + 20) - offset
    x2 = (obj.y + 20) - offset
    y1 = (obj.x + 20) + offset
    y2 = (obj.y + 20) + offset
    return (x1, x2, y1, y2)

def parsePoints(points): # This doesn't look so good. TODO make this better
    temp, temps = [], []
    for i in range(len(points)):
        # point = (120, 104)
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
    for obj in bmap[0]:
        # this *should* identify whether the object should be shown or not
        if obj.type == "Circle":
            if i >= obj.time - arms and i <= obj.time:
                buffer.append(obj)
        elif obj.type == "Slider":
            if i >= obj.time - arms and i <= obj.time + int(slider_end_time(obj)):
                buffer.append(obj)
        elif obj.type == "Spinner":
            if i >= obj.time and i <= int(obj.typedata):
                buffer.append(obj)
    return buffer

dirname = '{} - {}'.format(bmap[1]['title'], bmap[1]['version']) # this is our working directory
if not dirname in os.listdir('.'): os.mkdir(dirname) # makes our directory if it doesn't exist
cspx = cs_px(bmap[1]['cs'])
arms = ar_ms(bmap[1]['ar'])
objectbuffer = [] # controlled by the checkbuffer function
ts = [t/100.0 for t in range(101)]

start = time.perf_counter()

for i in range(int((bmap[0][-1].time + 2000) / 20)):
    i = (i + 1) * 20
    frame = Image.new('RGBA', (552, 424), (0, 0, 0, 255))
    draw = ImageDraw.Draw(frame)
    buffer = createbuffer(i)
    for obj in buffer:
        if obj.type == "Circle":
            draw.ellipse(circlecalc(obj, cspx / 2))
            draw.ellipse(circlecalc(obj, cspx / 2 + (cspx * .65)  * ((obj.time - i) / arms)))
        elif obj.type == "Slider":
            draw.ellipse(circlecalc(obj, cspx / 2))
            draw.ellipse(circlecalc(obj, cspx / 2 + (cspx * .65)  * ((obj.time - i) / arms)))
            points = [(obj.x + 20, obj.y + 20)]
            points.extend([(int(point.split(':')[0]) + 20, int(point.split(':')[1]) + 20) for point in obj.typedata.split('|') if ':' in point])
            segments, slider = parsePoints(points), []
            for red in segments:
                bezier = make_bezier(red)
                draw.line(bezier(ts))#, width=int(cspx))
        elif obj.type == "Spinner":
            x, y = 276, 212
            draw.ellipse((x - 100, y - 100, x + 100, y + 100))
    frame.save('{}/{}.png'.format(dirname, str(int(i / 20)).zfill(8)))
    sys.stdout.write('{:>7}/{} {:.2f}% done.\r'.format(int(i), int(bmap[0][-1].time + 2000), i / int(bmap[0][-1].time + 2000) * 100))

sys.stdout.write('{}[{}] by {}\n'.format(bmap[1]['title'], bmap[1]['version'], bmap[1]['creator']))
sys.stdout.write('CS: {}({}px) AR: {}({}ms)\n'.format(bmap[1]['cs'], cs_px(bmap[1]['cs']), bmap[1]['ar'], ar_ms(bmap[1]['ar'])))
sys.stdout.write('Took {:.2f} seconds to finish.\n'.format(time.perf_counter() - start))

# Since I want to use PIL and have no idea how to make a video from images in python
# I'll use ffmpeg from command line for now, possibly indefinite.
# ffmpeg -r 50 -f image2 -i maptitle/%08d.png -vframes 1000 -vcodec libx264 -crf 25  -pix_fmt yuv420p video.mp4