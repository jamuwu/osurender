#!/usr/bin/python3.6
# This script would probably be a lot better
# If it wasn't synchronous, if you know an
# Easy way for someone to learn to use
# Threads, please let me know :)
import os, sys, math, time, json, requests, numpy, imageio
from utils.parser import parseReplay, replayEvent
from utils.simulation import simulate, Timing
from PIL import Image, ImageDraw
from utils import pyttanko

info  = sys.stdout.write
error = sys.stderr.write

if len(sys.argv) < 2:
    error("You need to provide a map to render!\n")
    sys.exit(1)
else: filename = sys.argv[1]

settings = json.loads(open('config.json').read())
if settings['key'] == '':
    error('Please edit config.json with your api key!\n')
    sys.exit(1)

try: replay = parseReplay(filename)
except: # Error catching
    with open('errors.log', 'a') as f:
        f.write(f'{sys.exc_info()}\n')
    error("Sorry, something went wrong!\nPlease send your errors.log to @Jamu#2893 on Discord\n")
    sys.exit(1)

# I don't expect this to ever cause an error
bmaphash = replay['beatmap_md5']
data = requests.get(f"https://osu.ppy.sh/api/get_beatmaps?k={settings['key']}&h={bmaphash}").json()
if len(data) < 1:
    error('Sorry, couldn\'t download the beatmap for this replay!\n')
    sys.exit(1)
filename = f'beatmaps/{bmaphash}.osu'
if not os.path.exists(filename):
    r = requests.get(f"https://osu.ppy.sh/osu/{data[0]['beatmap_id']}", stream=True)
    with open(filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024): 
            if chunk: f.write(chunk)
bmap = pyttanko.parser().map(open(filename, encoding='utf-8'))
stars = pyttanko.diff_calc().calc(bmap, mods=replay['mods_bitwise'])
video = imageio.get_writer('{}-{}-{}.mp4'.format(bmap.title, bmap.version, replay['player']), fps=50)

# This is to allow me to accurately draw key presses
replay['replay_data'].reverse()

# found this on reddit
def cs_px(cs):
    if replay['mods']['hard_rock']: cs *= 1.3
    elif replay['mods']['easy']: cs /= 2
    return int(109 - 9 * cs)

# math from pyttanko without the variables
def ar_ms(ar):
    if replay['mods']['hard_rock']: ar *= 1.4
    elif replay['mods']['easy']: ar *= 0.5
    if ar < 5.0: arms = 1800 - 120 * ar
    else: arms = 1200 - 150 * (ar - 5)
    if replay['mods']['double_time'] or replay['mods']['nightcore']: arms /= 3/2
    if replay['mods']['half_time']: arms /= 3/4
    return int(arms)

# bezier code from https://stackoverflow.com/questions/246525/how-can-i-draw-a-bezier-curve-using-pythons-pil
# literally don't ask me because I have no idea what it's doing lmao
def make_bezier(xys):
    n = len(xys)
    combinations = pascal_row(n-1)
    def bezier(ts):
        result = []
        for t in ts:
            tpowers = (t**i for i in range(n))
            upowers = reversed([(1-t)**i for i in range(n)])
            coefs = [c*a*b for c, a, b in zip(combinations, tpowers, upowers)]
            result.append(
                tuple(sum([coef*p for coef, p in zip(coefs, ps)]) for ps in zip(*xys)))
        return result
    return bezier

# Stolen from Sunpy, source is https://github.com/osufx/osu-parser/blob/master/osu_parser/curves.py#L124
# Slightly modified as you can see, lol
def perfect(p):
    d = 2 * (p[0][0] * (p[1][1] - p[2][1]) + p[1][0] * (p[2][1] - p[0][1]) + p[2][0] * (p[0][1] - p[1][1]))
    if d == 0:
        # Perhaps this can be avoided? For now I'll return a bezier as that works
        bezier = make_bezier(p)
        return bezier(ts)
    ux = ((pow(p[0][1], 2) + pow(p[0][1], 2)) * (p[1][1] - p[2][1]) + (pow(p[1][0], 2) + pow(p[1][1], 2)) * (p[2][1] - p[0][1]) + (pow(p[2][0], 2) + pow(p[2][1], 2)) * (p[0][1] - p[1][1])) / d
    uy = ((pow(p[0][0], 2) + pow(p[0][1], 2)) * (p[2][0] - p[1][0]) + (pow(p[1][0], 2) + pow(p[1][1], 2)) * (p[0][0] - p[2][0]) + (pow(p[2][0], 2) + pow(p[2][1], 2)) * (p[1][0] - p[0][0])) / d
    px = ux - p[0][0]
    py = uy - p[0][1]
    r = pow(pow(px, 2) + pow(py, 2), 0.5)
    # I need to manually do the path which is sad
    # Because I suck at geometry and understanding it
    # This is currently not working and will likely
    # Need external help in fixing it, or at least
    # Teaching me what I need to know :^)
    return circumpoints(ux, uy, r)

def circumpoints(x, y, r, n=100):
    points = []
    for x in range(0, n + 1):
        points.append((
            x + (math.cos(2 * math.pi / n * x) * r),  # x
            y + (math.sin(2 * math.pi / n * x) * r)))  # y
    return points

def pascal_row(n):
    result = [1]
    x, numerator = 1, n
    for denominator in range(1, n//2+1):
        x *= numerator
        x /= denominator
        result.append(x)
        numerator -= 1
    if n&1 == 0: result.extend(reversed(result[:-1]))
    else: result.extend(reversed(result)) 
    return result

def slider_end_time(obj):
    timings = bmap.timing_points
    for timing in timings:
        if obj.time >= timing.time:
            t = timing
            break
    #return t.ms_per_beat * (obj.data.distance / px_per_beat) / 100 * obj.data.repetitions
    return obj.data.distance / (100 * bmap.sv) * t.ms_per_beat

def slider_curve(red): # I'll work on this later to make it actually work in producing true slider paths
    if   len(red) == 2: return red
    #elif len(red) == 3: return perfect(red) # TODO make this work
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

buffer = [] # This is because I can do this lol
objindex, replayindex, lifeindex = 0, 0, 0
def updatebuffer(i):
    # creates a new buffer containing only objects that are within the current time frame
    global objindex, replayindex, buffer # Because this is needed apparently? Never experienced this before...
    objdone, replaydone = False, False
    # I think seperating these will use less memory? Or at least make drawing each frame faster
    cursors, smokes = [], []
    # this *should* identify whether the object should be shown or not
    while not objdone:
        if objindex >= len(bmap.hitobjects): bjdone = True; break
        obj = bmap.hitobjects[objindex]
        if obj.objtype & 1<<0 != 0: # Circle
            if i >= (obj.time - arms) and i <= obj.time:
                buffer.append(obj)
                objindex += 1
            else: objdone = True
        elif obj.objtype & 1<<1 != 0: # Slider
            if i >= (obj.time - arms) and i <= (obj.time + int(slider_end_time(obj))):
                buffer.append(obj)
                objindex += 1
            else: objdone = True
        elif obj.objtype & 1<<3 != 0: # Spinner
            if i >= obj.time and i <= obj.endtime:
                buffer.append(obj)
                objindex += 1
            else: objdone = True
    # I think this is going to keep my life easy and allow me not to mess with anything
    # Regarding the fact that I'm rendering 50fps using a 60fps replay
    for event in replay['replay_data']:
        #if replayindex >= len(replay['replay_data']): replaydone = True; break
        if event.time >= i - 260 and event.time <= i + 10:
            cursors.append(event)
        if event.keys['SM']: 
            # I want smokes to mimick the behavior of the client but that's for later
            # For now I'll just make it show for 2 seconds
            if event.time >= i - 2010 and event.time <= i + 10:
                smokes.append((event.x + 20, event.y + 20))
    # Checks for expired objects in buffer
    newbuffer = []
    for obj in buffer:
        if obj.objtype & 1<<0 != 0: # Circle
            if i >= (obj.time - arms) and i <= obj.time:
                newbuffer.append(obj)
        elif obj.objtype & 1<<1 != 0: # Slider
            if i >= (obj.time - arms) and i <= (obj.time + int(slider_end_time(obj))) :
                newbuffer.append(obj)
        elif obj.objtype & 1<<3 != 0: # Spinner
            if i >= obj.time and i <= obj.endtime:
                newbuffer.append(obj)
    buffer = newbuffer
    return buffer, cursors, smokes

dirname = '{} - {}'.format(bmap.title, bmap.version) # this is our working directory
if not dirname in os.listdir('replays/'): os.mkdir(f'replays/{dirname}') # makes the directory if it doesn't exist
cspx = cs_px(bmap.cs)
arms = ar_ms(bmap.ar)
end_time = max([bmap.hitobjects[-1].time, replay['replay_data'][-1].time])
objectbuffer = [] # controlled by the checkbuffer function
ts = [t/100.0 for t in range(101)]
evals = {'300': 300, '100': 100, '50': 50, 'miss': 0}
evalcount = {'300': 0, '100': 0, '50': 0, 'miss': 0}

info(f'{bmap.title}[{bmap.version}] by {bmap.creator}\n')
info(f'CS: {bmap.cs}({cs_px(bmap.cs)}px) AR: {bmap.ar}({ar_ms(bmap.ar)}ms)\n')

start = time.perf_counter()
# Loops through the map generating a frame every 20ms
# Allowing us to gracefully make a 50fps video...
# For a 60fps video it'd be (1 / 60) / (1 / 100)
# You can probably work out why'd I'd rather stick
# To a clean number like 20 instead
for i in range(int((end_time) / 20)):
    i = (i + 1) * 20
    frame = Image.new('RGBA', (552, 424), (0, 0, 0, 255))
    draw = ImageDraw.Draw(frame)
    buffer, cursors, smokes = updatebuffer(i)
    keysdone = False
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
    # We want smoke to always be under the cursor
    draw.line(smokes, fill=(255, 255, 0))
    for cursor in cursors:
        x = cursor.x + 20
        y = cursor.y + 20
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(0, 255, 205))
        # Should I try doing something better with keys?
        if not keysdone:
            if cursor.keys['K1']: draw.rectangle((532, 172, 552, 192), fill=(225, 225, 225))
            if cursor.keys['K2']: draw.rectangle((532, 192, 552, 212), fill=(225, 225, 225))
            if cursor.keys['M1']: draw.rectangle((532, 212, 552, 232), fill=(225, 225, 225))
            if cursor.keys['M2']: draw.rectangle((532, 232, 552, 252), fill=(225, 225, 225))
            keysdone = True
    percent = i / int(end_time)
    # Progress bar
    draw.rectangle((0, 420, 551, 423))
    draw.rectangle((0, 420, int(550 * percent) + 1, 423), fill=(255, 255, 255))
    # Save the frame
    video.append_data(numpy.array(frame))
    info(f'{int(i):>7}/{int(end_time)} {percent * 100:.2f}% done.\r')

info(f'Took {time.perf_counter() - start:.2f} seconds to finish.\n')

# For audio I'll have to use ffmpeg for now...
# ffmpeg -i video.mp4 -i mapaudio.mp3 videowithaudio.mp4
# For DT/NC change -filter:a "atempo=1.5" after mapaudio.mp3
# For HT it's the same as DT/NC, just change atempo to 0.75 xd