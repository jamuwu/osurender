from struct import unpack_from, calcsize
from dataclasses import dataclass
import lzma, math

class Replay:
    def __init__(self, path):
        with open(path, 'rb') as f:
            self.data = f.read()
        self.offset = 0
        self.mode, self.version = self.unpack('<bi')
        self.beatmaphash = self._str()
        self.username = self._str()
        self.replayhash = self._str()
        stats = self.unpack('<hhhhhhih?i')
        self.n300, self.n100, self.n50, self.gekis = stats[0:4]
        self.katus, self.nmiss, self.score, self.combo = stats[4:8]
        self.perfect, self.mods = stats[8:10]
        self.lifebar = self._str()
        self.timestamp, self.replaylength = self.unpack('<qi')
        offsetend = self.offset + self.replaylength
        self.replaystring = lzma.decompress(self.data[self.offset:offsetend]).decode('ascii')[:-1]
        self.offset = offsetend
    
    def unpack(self, b):
        unpacked = unpack_from(b, self.data, self.offset)
        self.offset += calcsize(b)
        return unpacked

    def _dec(self):
        stringLength = 0
        shift = 0
        while True:
            byte = self.data[self.offset]
            self.offset += 1
            stringLength += (byte & 0b01111111) << shift
            if byte & 0b10000000 == 0x00:
                break
            shift += 7
        return stringLength

    def _str(self):
        if self.data[self.offset] == 0x00:
            self.offset += 1
        elif self.data[self.offset] == 0x0b:
            self.offset += 1
            stringLength = self._dec()
            offsetEnd = self.offset + stringLength
            string = self.data[self.offset:offsetEnd].decode('utf-8')
            self.offset += stringLength
            return string

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