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
        keys = {'M1': False, 'M2': False, 'K1': False, 'K2': False, 'SM': False}
        if z & 1 != 0 and z & 4 == 0: keys['M1'] = True
        if z & 2 != 0 and z & 8 == 0: keys['M2'] = True
        if z & 4 != 0:  keys['K1'] = True
        if z & 8 != 0:  keys['K2'] = True
        if z & 16 != 0: keys['SM'] = True # Smoke???

        time += int(w)
        if time > 0:
            action = replayEvent(time, float(x), float(y), keys)
            actions.append(action)

    return actions

def parseLifeGraph(graphString):
    result = []
    life = graphString.split(',')
    for hp in life:
        if hp != '':
            pos = hp.split('|')
            x = float(pos[0])
            y = float(pos[1])
            result.append((x, y))
    return result

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
    data['mods_bitwise'] = mods
    graphString, offset = parseString(osr, offset)
    data['life_graph'] = parseLifeGraph(graphString)
    data['time_stamp'], offset = parseDate(osr, offset)
    data_len, offset = parseNum(osr, offset, 4)
    replay_str = str(lzma.decompress(osr[offset:offset+data_len]), 'utf-8')
    data['replay_data'] = parseReplayString(replay_str)

    return data