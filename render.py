import os, sys
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.animation import FuncAnimation

from resize import resize
from parsers import parseReplay, parse_osu
from bezier import bezier_curve_range as bezier

if len(sys.argv) > 1:
    filename = sys.argv[1]

if not os.path.exists('{}.osr'.format(filename)) or not os.path.exists('{}.osu'.format(filename)):
    raise ValueError("""Please make sure to specify a 
        name that both the .osr and .osu files share.""")

try:
    resize(512, 384, '{}.jpg'.format(filename))
    img = plt.imread('image.jpg')
except:
    img = plt.imread('image.jpg')

start = datetime.now()

# Keep in mind an osu replay is by nature 60 fps
targetfps = 60
framedelay = (1 / targetfps) / (1 / 1000)
# Opens and Parses the replay file
replay = parseReplay('{}.osr'.format(filename))
btmap = parse_osu('{}.osu'.format(filename))
print("Replay and beatmap parsed")
objs = btmap[0]
boffset = objs[0].time
rgraph = replay['life_graph']
rmaxtime, bmaxtime = replay['replay_data'][-1].time, objs[-1].time
events, hobjbuf, oobjbuf = [], [], []
# Sets the plot window size to be 1:1 with osu pixels
xwinmax = 512
ywinmax = 384
xwinmin = 0
ywinmin = 0
replayframes = len(replay['replay_data'])
totalkeys = {'K1':0, 'K2':0, 'M1':0, 'M2':0}
keystate = {'K1': False, 'K2': False, 'M1': False, 'M2': False}
fig, ax = plt.subplots()
fig.set_tight_layout(True)
ax.xaxis.set_visible(False)
ax.yaxis.set_visible(False)

# Processes which keys are pressed during the curent event
def process_keys(pressed, totalkeys, keystate):
    for k in ['K1', 'K2', 'M1', 'M2']:
        if pressed[k] and not keystate[k]:
            totalkeys[k] += 1
            keystate[k] = True
        elif pressed[k] and keystate[k]:
            keystate[k] = True
        elif not pressed[k] and keystate[k]:
            keystate[k] = False
    return totalkeys

# get the timing window for a note with the given OD and mods
def timing_window(od, hd, ez):
    mod_od = od
    if ez:
        mod_od = 0.5 * od
    elif hd:
        mod_od = min(1.4 * od, 10)

    w300 = 79.5 - 6.0 * mod_od
    w100 = 139.5 - 8.0 * mod_od
    w50 = 199.5 - 10.0 * mod_od

    return (w300, w100, w50)

def in_window(obj, time, window):
    return obj.time - window[2] <= time and \
        obj.time + window[2] >= time

def circle_radius(cs, hd, ez):
    mod_cs = cs
    if hd:
        mod_cs *= 1.3
    elif ez:
        mod_cs /= 2
    return (10 - mod_cs) * 100

def dist(p_input, obj):
    return math.sqrt(math.pow(p_input['x'] - obj.x, 2) + \
        math.pow(p_input['y'] - obj.y, 2))

def calc_dist(points):
    dist = 0
    for red in points:
        segments.extend(list(bezier(200, red)))
    for i in range(len(segments)):
        if i + 1 != len(segments):
            dist += (segments[i + 1] - segments[i]) ** 2
    return math.sqrt(dist)

def get_current_timing(i):
    timings = btmap[2]
    for timing in timings:
        if i.time >= timing.time:
            return timing

def slider_end_time(obj):
    currentSection = get_current_timing(obj)
    pxPerBeat = btmap[1]['slider_multiplier'] * 100 * currentSection.time
    beatsNumber = (obj.pixellength * obj.repeat) / pxPerBeat
    msLength = beatsNumber * currentSection.mpb
    return msLength * 100

def score_hit(time, obj, window):
    if obj.lenient and abs(time - obj.time) <= window[2]:
        return '300'
    if abs(time - obj.time) <= window[0]:
        return '300'
    elif abs(time - obj.time) <= window[1]:
        return '100'
    elif abs(time - obj.time) <= window[2]:
        return '50'
    return 'welp'

def scale_number(unscaled, to_min, to_max, from_min, from_max):
    return (to_max-to_min)*(unscaled-from_min)/(from_max-from_min)+to_min

def scale_list(l, to_min, to_max):
    return [scale_number(i, to_min, to_max, min(l), max(l)) for i in l]

def time_ago(time1, time2):
    time_diff = time1 - time2
    timeago = datetime(1,1,1) + time_diff
    time_limit = 0
    time_ago = ""
    if timeago.year-1 != 0:
        time_ago += "{} Year{} ".format(timeago.year-1, determine_plural(timeago.year-1))
        time_limit = time_limit + 1
    if timeago.month-1 !=0:
        time_ago += "{} Month{} ".format(timeago.month-1, determine_plural(timeago.month-1))
        time_limit = time_limit + 1
    if timeago.day-1 !=0 and not time_limit == 2:
        time_ago += "{} Day{} ".format(timeago.day-1, determine_plural(timeago.day-1))
        time_limit = time_limit + 1
    if timeago.hour != 0 and not time_limit == 2:
        time_ago += "{} Hour{} ".format(timeago.hour, determine_plural(timeago.hour))
        time_limit = time_limit + 1
    if timeago.minute != 0 and not time_limit == 2:
        time_ago += "{} Minute{} ".format(timeago.minute, determine_plural(timeago.minute))
        time_limit = time_limit + 1
    if not time_limit == 2:
        time_ago += "{} Second{} ".format(timeago.second, determine_plural(timeago.second))
    return time_ago

def determine_plural(number):
    if int(number) != 1:
        return 's'
    else:
        return ''

def parsePoints(points):
    temp, temps = [], []
    for i in range(len(points)):
        # point = (120, 104)
        temp.append(points[i])
        if i + 1 < len(points):
            if points[i] == points[i + 1]:
                temps.append(temp)
                temp = [points[i]]
        else:
            temps.append(temp)
    return temps

def update(i):
    if i <= replayframes:
        ax.cla()
        plt.xlim(xwinmin - 10, xwinmax + 10)
        plt.ylim(ywinmin - 10, ywinmax + 10)
        #ax.imshow(img, extent=[xwinmin - 10, xwinmax + 10, ywinmin - 10, ywinmax + 10])
        event = replay['replay_data'][min(i, replayframes - 1)]
        events.append(event)
        if len(events) > 10: # This basically determines the trail length
            events.pop(0)
        x, y, objx, objy = [], [], [], []
        for cursorcoords in events:
            x.append(cursorcoords.x)
            y.append(384 - cursorcoords.y)
        if len(objs) > 0:
            if event.time - 10 <= objs[0].time + replay['replay_data'][0].time and event.time + 500 >= objs[0].time + replay['replay_data'][0].time:
                if objs[0].type == "Circle":
                    hobjbuf.append((0, objs[0]))
                else:
                    oobjbuf.append(objs[0])
                objs.pop(0)
            for num, obj in enumerate(hobjbuf):
                if obj[0] <= 45:
                    hobjbuf[num] = (obj[0] + 1, obj[1])
                    objx.append(obj[1].x)
                    if replay['mods']['hard_rock']:
                        objy.append(obj[1].y)
                    else:
                        objy.append(384 - obj[1].y)
        if len(hobjbuf) > 0:
            if hobjbuf[0][0] > 45: # This is the number of frames each hitcircle will stay rendered
                hobjbuf.pop(0)
        circles = ax.scatter(objx, objy, s=circle_radius(btmap[1]['cs'], replay['mods']['hidden'], replay['mods']['easy']), color='#00FFC0')
        oobjdraw = []
        for obj in oobjbuf: # Parse the objects if there's objects other than a circle
            objectdata = {'points': []}
            segments = []
            if obj.type == "Slider":
                segments = []
                objectdata['type'] = [point for point in obj.typedata.split('|') if ':' not in point][0]
                objectdata['starttime'] = obj.time
                objectdata['points'] = [(obj.x, obj.y)]
                objectdata['points'].extend([(int(point.split(':')[0]), int(point.split(':')[1])) for point in obj.typedata.split('|') if ':' in point])
                objectdata['endtime'] = obj.time + int(slider_end_time(obj))
                parsedpoints = parsePoints(objectdata['points'])
                for red in parsedpoints:
                    segments.extend(list(bezier(50, red)))
            if obj.type == "Spinner":
                objectdata['starttime'] = obj.time
                objectdata['points'] = [(obj.x, obj.y)]
                objectdata['endtime'] = int(obj.typedata)
            if event.time >= objectdata['endtime']:
                oobjbuf.pop(oobjbuf.index(obj))
            oobjdraw.append((segments, objectdata))
        for segment, obj in oobjdraw:
            if len(oobjdraw) != 0:
                if event.time <= obj['endtime']:
                    ax.scatter([point[0] for point in segment], [(384 - point[1], point[1])[replay['mods']['hard_rock']] for point in segment], s=circle_radius(btmap[1]['cs'], replay['mods']['hidden'], replay['mods']['easy']), color='#00FFC0')
        ax.scatter(x, y, label=replay['player'], s=100, color='#FF9BBA')
        ax.legend(loc='best')
        keys = process_keys(event.keys, totalkeys, keystate)
        keytext = "K1: {}\nK2: {}\nM1: {}\nM2: {}".format(keys['K1'], keys['K2'], keys['M1'], keys['M2'])
        ax.annotate(keytext, xy=(0, 0), horizontalalignment='left', verticalalignment='bottom', color='red')
        rendered = i * 16.666666666666668 / 1000
        sys.stdout.write("\rRendered {:.2f} Seconds in {}{:.2f}% Complete".format(rendered, time_ago(datetime.now(), start), (i / replayframes) * 100))
        sys.stdout.flush()
        return circles, ax
    if i > replayframes:
        ax.cla()
        plt.xlim(0, 6)
        plt.ylim(0, 6)
        ax.imshow(img, extent=[0, 6, 0, 6])
        timestamp = datetime.utcfromtimestamp(replay['time_stamp']).strftime('%Y-%m-%d %H:%M:%S')
        mapinfo = "{}[{}]\nCreated by {}\nPlayed by {} on {}".format(btmap[1]['title'], btmap[1]['version'], btmap[1]['creator'], replay['player'], timestamp)
        ax.annotate(mapinfo, xy=(0.05, 5.95), horizontalalignment='left', verticalalignment='top', color='white')
        ax.add_patch(patches.Rectangle((0, 6), 6, -5, alpha=0.5, facecolor='#00FFC0'))
        ax.annotate(replay['score'], xy=(5, 5), horizontalalignment='right', verticalalignment='top', color='black', size=15)
        ax.annotate(replay['num_miss'], xy=(5, 2), horizontalalignment='right', verticalalignment='top', color='black', size=15)
        ax.annotate(replay['num_50'], xy=(2, 2), horizontalalignment='right', verticalalignment='top', color='black')
        ax.annotate(replay['num_100'], xy=(2, 3), horizontalalignment='right', verticalalignment='top', color='black', size=15)
        ax.annotate(replay['num_katu'], xy=(5, 3), horizontalalignment='right', verticalalignment='top', color='black', size=15)
        ax.annotate(replay['num_geki'], xy=(5, 4), horizontalalignment='right', verticalalignment='top', color='black', size=15)
        ax.annotate(replay['num_300'], xy=(2, 4), horizontalalignment='right', verticalalignment='top', color='black', size=15)
        ax.add_patch(patches.Rectangle((4, 1), 2, -1, alpha=0.5, facecolor='black'))
        boxes = (patches.Rectangle((2.25, 1.2), 0.01, 3.1, color='black'), patches.Rectangle((0, 2.3), 4.5, 0.01, color='black'), patches.Rectangle((0, 3.3), 4.5, 0.01, color='black'), patches.Rectangle((0, 4.3), 4.5, 0.01, color='black'))
        rgraphx = scale_list(rgraph[0], 4, 6)
        rgraphy = [point - 0.05 for point in rgraph[1]]
        if rgraphx == [] and rgraphy == []:
            rgraphx = scale_list([objects[0].time, objects[-1].time], 4, 6)
            rgraphy = [0.95, 0.95]
        for box in boxes:
            ax.add_patch(box)
        circles = ax.plot(rgraphx, rgraphy)
        return circles, ax

anim = FuncAnimation(fig, update, frames=np.arange(0, replayframes + 240), interval=framedelay)
plt.show()
#anim.save('replay-{}-{}-{}.mp4'.format(btmap[1]['title'], btmap[1]['version'], replay['player']))
sys.stdout.write("\nFinished Rendering in {}\n".format(time_ago(datetime.now(), start)))

