from collections import deque
import math, json, sys, os
import numpy as np

# constants
HITMAP_RESOLUTION = 64
HITMAP_SIZE = 500
TIMING_RESOLUTION = 64

def timing_window(od, hd, ez):
    mod_od = od
    if ez: mod_od = 0.5 * od
    elif hd: mod_od = min(1.4 * od, 10)
    w300 = 79.5 - 6.0 * mod_od
    w100 = 139.5 - 8.0 * mod_od
    w50 = 199.5 - 10.0 * mod_od
    return (w300, w100, w50)

def in_window(obj, time, window):
    return obj.time - window[2] <= time and obj.time + window[2] >= time

def pushed_buttons(prev_input, cur_input):
    buttons = []
    for k in ['K1', 'K2', 'M1', 'M2']:
        if cur_input.keys[k] and not prev_input.keys[k]:
            buttons.append(k)
    return buttons

def circle_radius(cs, hd, ez):
    mod_cs = cs
    if hd: mod_cs *= 1.3
    elif ez: mod_cs /= 2
    return (104.0 - mod_cs * 8.0) / 2.0

def dist(p_input, obj):
    return math.sqrt(math.pow(p_input.x - obj.data.pos.x, 2) + math.pow(p_input.y - obj.data.pos.y, 2))

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

class Timing:
    def __init__(self, time, event, timing, x, y):
        self.time = int(time)
        self.event = event
        self.timing = timing
        self.x, self.y = int(x), int(y)
    
    def __repr__(self):
        return f'{self.event}:{self.time}:{self.timing}:{self.x}:{self.y}'

def simulate(bmap, replay):
    mods = replay['mods']
    WINDOW = timing_window(bmap.od, mods['hard_rock'], mods['easy'])
    RADIUS = circle_radius(bmap.cs, mods['hard_rock'], mods['easy'])
    replay_data = replay['replay_data']
    objects = bmap.hitobjects
    end_time = max([objects[-1].time, replay_data[-1].time])
    bmap.length = objects[-1].time
    inputs = replay_data
    print(inputs)
    objects = objects
    cur_input = {'time': -1, 'keys': {'M1': False, 'M2': False, 'K1': False, 'K2': False}}
    prev_obj = None
    cur_obj = None
    marked = False
    timeline = []
    keys = {'M1': 0, 'M2': 0, 'K1': 0, 'K2': 0}
    hitmap = np.zeros((HITMAP_RESOLUTION, HITMAP_RESOLUTION))
    timings = np.zeros(TIMING_RESOLUTION)
    all_timings = []
    extra_inputs = []
    missed_notes = []
    if mods['hard_rock']:
        for o in objects:
            o.data.pos.y = 384 - o.data.pos.y
    for time in range(end_time):
        if len(inputs) > 0:
            next_input = inputs[0]
            if time > next_input.time:
                prev_input = cur_input
                cur_input = inputs.pop(0)
                buttons = pushed_buttons(prev_input, cur_input)
                if len(buttons) > 0:
                    for k in buttons:
                        keys[k] += 1
                    if cur_obj != None and dist(cur_input, cur_obj) < RADIUS:
                        score_val = score_hit(time, cur_obj, WINDOW)
                        time_diff = time - cur_obj.time
                        bucket = int(time_diff / (WINDOW[2] * 2) * \
                            TIMING_RESOLUTION) + int(TIMING_RESOLUTION / 2)
                        if bucket >= 0 and bucket < len(timings):
                            timings[bucket] += 1
                        all_timings.append(time_diff)
                        if score_val != 'welp':
                            timeline.append(Timing(time, score_val, time_diff, cur_input.x, cur_input.y))
                        prev_obj = cur_obj
                        cur_obj = None                        
                    else:
                        extra_inputs.append(cur_input)
        if cur_obj != None and time > cur_obj.time + WINDOW[2]:
            #timeline.append(Timing(cur_obj.time, 'miss', 0, cur_obj.data.pos.x, cur_obj.data.pos.y))
            event = {
                't': cur_obj.time,
                'event': 'miss',
                'timing': 0,
                'xi': -1,
                'yi': -1
            }
            missed_notes.append({
                'prev': prev_obj,
                'cur': cur_obj,
                'event': event
            })
            prev_obj = cur_obj
            cur_obj = None
        if len(objects) > 0:
            next_obj = objects[0]
            if cur_obj == None and in_window(next_obj, time, WINDOW):
                cur_obj = objects.pop(0)
    for note in missed_notes:
        cur_obj = note['cur']
        prev_obj = note['prev']
        event = note['event']
        for cur_input in extra_inputs:
            if in_window(cur_obj, cur_input.time, WINDOW):
                xi, yi = transform_coords(cur_input, prev_obj, cur_obj)
                time_diff = cur_input.time - cur_obj.time
                event['timing'] = time_diff
                event['xi'] = xi
                event['yi'] = yi
    unstable_rate = np.std(all_timings) * 10
    result = {
        'timeline': timeline,
        'keys': dict(keys),
        'circle_size': RADIUS,
        'unstable_rate': unstable_rate
    }
    return result