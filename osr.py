from struct import unpack_from, calcsize
from dataclasses import dataclass
import numpy as np
import lzma, math


def parse(filename):
    with open(filename, 'rb') as f:
        return Replay(*_parse(f.read()))


def _parse(data):
    global offset
    offset = 0

    def _dec():
        global offset
        stringLength = 0
        shift = 0
        while True:
            byte = data[offset]
            offset += 1
            stringLength += (byte & 0b01111111) << shift
            if byte & 0b10000000 == 0x00:
                break
            shift += 7
        return stringLength

    def _str():
        global offset
        if data[offset] == 0x00:
            offset += 1
        elif data[offset] == 0x0b:
            offset += 1
            stringLength = _dec()
            offsetEnd = offset + stringLength
            string = data[offset:offsetEnd].decode('utf-8')
            offset += stringLength
            return string

    # Game mode and game version
    gameMode, gameVersion = unpack_from('<bi', data, offset)
    offset += calcsize('<bi')
    # Beatmap hash
    bmapHash = _str()
    # Player username
    username = _str()
    # Replay hash
    replayHash = _str()
    # Unpacking score stats
    n300, n100, n50, gekis, katus, nmiss, score, maxCombo, perfect, mods = unpack_from(
        '<hhhhhhih?i', data, offset)
    offset += calcsize('<hhhhhhih?i')
    # Life bar
    lifeBar = _str()
    # Replay timestamp and replay length
    timestamp, replayLength = unpack_from('<qi', data, offset)
    offset += calcsize('<qi')
    # Replay string
    offsetEnd = offset + replayLength
    replayString = lzma.decompress(data[offset:offsetEnd]).decode('ascii')[:-1]
    offset = offsetEnd

    return (gameMode, gameVersion, bmapHash, replayHash, username, n300, n100,
            n50, gekis, katus, nmiss, score, maxCombo, perfect, mods, lifeBar,
            timestamp, replayLength, replayString)


@dataclass
class Replay:
    mode: int
    version: int
    beatmaphash: str
    replayhash: str
    username: str
    n300: int
    n100: int
    n50: int
    gekis: int
    katus: int
    nmiss: int
    score: int
    combo: int
    perfect: bool
    mods: int
    lifebar: str
    timestamp: int
    replaylength: int
    replaystring: str

    @property
    def events(self):
        index = 0
        time = 0
        stringlength = len(self.replaystring) - 1
        while index < stringlength:
            event = ''
            while (char := self.replaystring[index]) != ',':
                event += char
                index += 1
                if index >= stringlength:
                    break
            index += 1
            w, x, y, _ = event.split('|')
            # -12345 has the rng seed on z, don't need it
            if w == '-12345':
                break
            time += abs(int(w))
            yield [float(x), float(y), time]
    
    @property
    def frames(self):
        linear = lambda x1, x2, r: ((1 - r) * x1[0] + r * x2[0], (1 - r) * x1[1] + r * x2[1])
        events = self.events
        prevent = next(events)
        time = prevent[2]
        window = []
        while event := next(events, False):
            while event[2] < time:
                prevent = event
                if event := next(events, False):
                    break
            dt1 = time - prevent[2]
            dt2 = event[2] - prevent[2]
            time += 1000 / 60
            window.append(linear(prevent, event, dt1 / dt2))
            window = window[-5:]
            yield window

    def __repr__(self):
        return f'{self.username} - {self.replayhash} ({self.timestamp})'