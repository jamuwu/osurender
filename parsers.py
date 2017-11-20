import json
import sys
from struct import unpack_from
import lzma

def parseNum(db, offset, length):
    typeMap = {1:'B', 2:'H', 4:'I', 8:'Q'}
    numType = typeMap[length]
    val = unpack_from(numType, db, offset)[0]
    return (val, offset+length)

def parseDate(db, offset):
    val = unpack_from('Q', db, offset)[0]
    return ((val / 10000000.0) - 62135596800, offset+8)

def parseFloat(db, offset, length):
    typeMap = {4:'f', 8:'d'}
    numType = typeMap[length]
    val = unpack_from(numType, db, offset)[0]
    return (val, offset+length)

def parseBool(db, offset):
    val = unpack_from('b', db, offset)[0]
    if val == 0x00:
        return (False, offset+1)
    else:
        return (True, offset+1)

def parseString(db, offset):
    existence = unpack_from('b', db, offset)[0]
    if existence == 0x00:
        return (u'', offset+1)
    elif existence == 0x0b:
        # decode ULEB128
        length = 0
        shift = 0
        offset += 1
        while True:
            val = unpack_from('B', db, offset)[0]
            length |= ((val & 0x7F) << shift)
            offset += 1
            if (val & (1 << 7)) == 0:
                break
            shift += 7

        string = unpack_from(str(length)+'s', db, offset)[0]
        offset += length

        unic = u''
        try:
            unic = str(string, 'utf-8')
        except UnicodeDecodeError:
            print("Could not parse UTF-8 string, returning empty string.")

        return (unic, offset)

def parseScore(db, offset):
    score = {}
    score['mode'], offset = parseNum(db, offset, 1)
    score['version'], offset = parseNum(db, offset, 4)
    score['md5'], offset = parseString(db, offset)
    score['player'], offset = parseString(db, offset)
    score['replay_md5'], offset = parseString(db, offset)
    score['num_300'], offset = parseNum(db, offset, 2)
    score['num_100'], offset = parseNum(db, offset, 2)
    score['num_50'], offset = parseNum(db, offset, 2)
    score['num_geki'], offset = parseNum(db, offset, 2)
    score['num_katu'], offset = parseNum(db, offset, 2)
    score['num_miss'], offset = parseNum(db, offset, 2)
    score['score'], offset = parseNum(db, offset, 4)
    score['max_combo'], offset = parseNum(db, offset, 2)
    score['perfect_combo'], offset = parseBool(db, offset)
    modFlags, offset = parseNum(db, offset, 4)
    score['mods'] = parseMods(modFlags)
    empty, offset = parseString(db, offset)
    score['timestamp'], offset = parseDate(db, offset)
    fff, offset = parseNum(db, offset, 4)
    score['score_id'], offset = parseNum(db, offset, 8)

    # no mod flag
    if not any(score['mods'].values()):
        score['mods']['no_mod'] = True
    else:
        score['mods']['no_mod'] = False

    # accuracy calculation
    misses = score['num_miss']
    num300 = score['num_300']
    num100 = score['num_100']
    num50 = score['num_50']
    numGeki = score['num_geki']
    numKatu = score['num_katu']

    # osu!std
    if score['mode'] == 0:
        numNotes = misses + num300 + num100 + num50
        weightedScore = num300 + num100 * 2.0/6.0 + num50 * 1.0/6.0
        score['accuracy'] = weightedScore / numNotes

        if score['accuracy'] == 1.0:
            score['grade'] = 'SS'
        elif float(num300) / numNotes >= 0.9 \
            and float(num50) / numNotes <= 0.1 \
            and misses == 0:
            score['grade'] = 'S'
        elif float(num300) / numNotes >= 0.8 and misses == 0 \
            or float(num300) / numNotes >= 0.9:
            score['grade'] = 'A'
        elif float(num300) / numNotes >= 0.7 and misses == 0 \
            or float(num300) / numNotes >= 0.8:
            score['grade'] = 'B'
        elif float(num300) / numNotes >= 0.6:
            score['grade'] = 'C'
        else:
            score['grade'] = 'D'

    # taiko
    elif score['mode'] == 1:        
        numNotes = misses + num300 + num100
        weightedScore = num300 + num100 * 0.5
        score['accuracy'] = weightedScore / numNotes

        if score['accuracy'] == 1.0:
            score['grade'] = 'SS'
        elif float(num300) / numNotes >= 0.9 \
            and misses == 0:
            score['grade'] = 'S'
        elif float(num300) / numNotes >= 0.8 and misses == 0 \
            or float(num300) / numNotes >= 0.9:
            score['grade'] = 'A'
        elif float(num300) / numNotes >= 0.7 and misses == 0 \
            or float(num300) / numNotes >= 0.8:
            score['grade'] = 'B'
        elif float(num300) / numNotes >= 0.6:
            score['grade'] = 'C'
        else:
            score['grade'] = 'D'

    # catch the beat
    elif score['mode'] == 2:
        numNotes = num300 + num100 + num50 + misses + numKatu
        weightedScore = num300 + num100 + num50
        score['accuracy'] = float(weightedScore) / numNotes

        if score['accuracy'] == 1.0:
            score['grade'] = 'SS'
        elif score['accuracy'] > .98:
            score['grade'] = 'S'
        elif score['accuracy'] > .94:
            score['grade'] = 'A'
        elif score['accuracy'] > .90:
            score['grade'] = 'B'
        elif score['accuracy'] > .85:
            score['grade'] = 'C'
        else:
            score['grade'] = 'D'

    # osu mania
    elif score['mode'] == 3:
        numNotes = numGeki + num300 + numKatu + num100 + num50 + misses
        weightedScore = numGeki + num300 + numKatu * 2.0/3.0 \
            + num100 * 1.0/3.0 + num50 * 1.0/6.0
        score['accuracy'] = weightedScore / numNotes


        if score['accuracy'] == 1.0:
            score['grade'] = 'SS'
        elif score['accuracy'] > .95:
            score['grade'] = 'S'
        elif score['accuracy'] > .90:
            score['grade'] = 'A'
        elif score['accuracy'] > .80:
            score['grade'] = 'B'
        elif score['accuracy'] > .70:
            score['grade'] = 'C'
        else:
            score['grade'] = 'D'

    return (score, offset)

def parseMods(modFlags):
    mods = ['no_fail', 'easy', 'no_video', 'hidden', 'hard_rock', \
    'sudden_death', 'double_time', 'relax', 'half_time', 'nightcore', \
    'flashlight', 'autoplay', 'spun_out', 'auto_pilot', 'perfect', \
    'key4', 'key5', 'key6', 'key7', 'key8', 'fade_in', 'random', \
    'cinema', 'target_practice', 'key9', 'coop', 'key1', 'key3', 'key2']

    modObject = {}
    for i, mod in enumerate(mods):
        if (modFlags & (1 << i)) != 0:
            modObject[mod] = True
        else:
            modObject[mod] = False
    return modObject

class replayEvent:
    def __init__(self, time, x, y, keys):
        self.time = time
        self.x = x
        self.y = y
        self.keys = keys

def parseReplayString(replayString):
    time = 0
    records = replayString.split(',')[:-1]
    actions = []
    for record in records:
        w, x, y, z = record.split('|')
        z = int(z)
        keys = {'M1': False, 'M2': False, 'K1': False, 'K2': False}
        if z == 1:
            keys['M1'] = True
        elif z == 2:
            keys['M2'] = True
        elif z == 3:
            keys['M1'] = True
            keys['M2'] = True
        elif z == 5:
            keys['K1'] = True
        elif z == 10:
            keys['K2'] = True
        elif z == 15:
            keys['K1'] = True
            keys['K2'] = True

        time += int(w)
        if time > 0:
            action = replayEvent(time, float(x), float(y), keys)
            actions.append(action)

    return actions

def parseLifeGraph(graphString):
    x, y = [], []
    life = graphString.split(',')
    for hp in life:
        if hp != '':
            pos = hp.split('|')
            x.append(float(pos[0]))
            y.append(float(pos[1]))
    return (x, y)

def parseReplay(filename):
    osr = open(filename, 'rb').read()
    offset = 0
    data = {}
    data['mode'], offset = parseNum(osr, offset, 1)
    data['version'], offset = parseNum(osr, offset, 4)
    data['beatmap_md5'], offset = parseString(osr, offset)
    data['player'], offset = parseString(osr, offset)
    data['player_lower'] = data['player'].lower()
    data['replay_md5'], offset = parseString(osr, offset)
    data['num_300'], offset = parseNum(osr, offset, 2)
    data['num_100'], offset = parseNum(osr, offset, 2)
    data['num_50'], offset = parseNum(osr, offset, 2)
    data['num_geki'], offset = parseNum(osr, offset, 2)
    data['num_katu'], offset = parseNum(osr, offset, 2)
    data['num_miss'], offset = parseNum(osr, offset, 2)
    data['score'], offset = parseNum(osr, offset, 4)
    data['max_combo'], offset = parseNum(osr, offset, 2)
    data['perfect_combo'], offset = parseNum(osr, offset, 1)
    mods, offset = parseNum(osr, offset, 4)
    data['mods'] = parseMods(mods)
    graphString, offset = parseString(osr, offset)
    # it's not here! generated by the game apparently
    # but I'll try my best to do it
    data['life_graph'] = parseLifeGraph(graphString)
    data['time_stamp'], offset = parseDate(osr, offset)
    data_len, offset = parseNum(osr, offset, 4)
    replay_str = str(lzma.decompress(osr[offset:offset+data_len]), 'utf-8')
    data['replay_data'] = parseReplayString(replay_str)

    return data

class HitObject:
    x = -1
    y = -1
    time = -1
    lenient = False

    def __init__(self, x, y, time, lenient, typedata, repeat=0, length=0):
        self.x = x
        self.y = y
        self.time = time
        self.lenient = lenient
        self.typedata = typedata
        self.type = ("Circle", ("Slider", "Spinner")[self.lenient == False])[self.typedata != ""]
        self.tags = []
        self.repeat = repeat
        self.pixellength = length

    def add_tag(self, tag):
        if tag not in self.tags:
            self.tags.append(tag)

    def __str__(self):
        return '(%d, %d, %d, %s, %s, %s)' % \
            (self.time, self.x, self.y, self.type, self.typedata, self.tags)

class TimingPoint:
    time = -1
    mpb = -1

    def __init__(self, time, mpb, velocity):
        self.time = time
        self.mpb = mpb
        self.velocity = velocity

def parse_object(line):
    params = line.split(',')
    x = float(params[0])
    y = float(params[1])
    time = int(params[2])

    objtype = int(params[3])
    # hit circle
    if (objtype & 1) != 0:
        return HitObject(x, y, time, False, "")

    # sliders
    # x,y,time,type,hitSound,sliderType|curveX:curveY|...,repeat,pixelLength,edgeHitsound,edgeAddition,addition
    elif (objtype & 2) != 0:
        return HitObject(x, y, time, True, params[5], repeat=int(params[6]), length=float(params[7]))

    # ignore spinners
    else:
        return HitObject(x, y, time, False, params[5]) 

"""
Takes a beatmap file as input, and outputs a list of
beatmap objects, sorted by their time offset.
"""
def parse_osu(filename):
    osu = open(filename)
    objects = []
    timing_points = []
    beatmap = {}
    in_objects = False
    in_timings = False
    # parse the osu! file
    for line in osu:
        if 'CircleSize' in line:
            beatmap['cs'] = float(line.split(':')[1])
        elif 'OverallDifficulty' in line:
            beatmap['od'] = float(line.split(':')[1])
        elif 'HPDrainRate' in line:
            beatmap['hp'] = float(line.split(':')[1])
        elif 'ApproachRate' in line:
            beatmap['ar'] = float(line.split(':')[1])
        elif 'SliderMultiplier' in line:
            beatmap['slider_multiplier'] = float(line.split(':')[1])
        elif 'SliderTickRate' in line:
            beatmap['slider_tick_rate'] = float(line.split(':')[1])
        elif 'Mode' in line:
            mode = int(line.split(':')[1])
        elif 'Title' in line and 'Unicode' not in line:
            beatmap['title'] = line.split(':')[1].strip()
            beatmap['title_lower'] = beatmap['title'].lower()
        elif 'Version' in line:
            beatmap['version'] = line.split(':')[1].strip()
            beatmap['version_lower'] = beatmap['version'].lower()
        elif 'Artist' in line and 'Unicode' not in line:
            beatmap['artist'] = line.split(':')[1].strip()
            beatmap['artist_lower'] = beatmap['artist'].lower()
        elif 'Creator' in line:
            beatmap['creator'] = line.split(':')[1].strip()
            beatmap['creator_lower'] = beatmap['creator'].lower()
        elif 'BeatmapID' in line:
            beatmap['beatmap_id'] = line.split(':')[1].strip()
        elif 'BeatmapSetID' in line:
            beatmap['beatmap_set_id'] = line.split(':')[1].strip()

        elif '[TimingPoints]' in line:
            in_timings = True
        elif in_timings:
            if line.strip() == '':
                # 45,288.461538461538,4,2,0,100,1,0
                # time, mpb, timingsignature
                in_timings = False
                continue

            args = line.split(',')
            time = float(args[0])
            mpb = float(args[1])
            velocity = 1
            if mpb > 0:
                pt = TimingPoint(time, mpb, velocity)
                timing_points.append(pt)
            else:
                pt = TimingPoint(time, mpb, abs(100 / mpb))
                timing_points.append(pt)

        if '[HitObjects]' in line:
            in_objects = True
        elif in_objects:
            obj = parse_object(line)
            if obj != None:
                objects.append(obj)

    # find streams
    for i in range(len(objects) - 1):
        obj0 = objects[i]
        obj1 = objects[i+1]
        # get current mpb
        mpb = -1
        for t in timing_points:
            mpb = t.mpb
            if obj0.time >= t.time:
                break

        timing_diff = obj1.time - obj0.time
        # print(str(timing_diff) + ' ' + str(mpb/4 + 10))

        if timing_diff < mpb/4.0 + 10.0:
            obj0.add_tag('stream')
            obj1.add_tag('stream')

    return (objects, beatmap, timing_points)
