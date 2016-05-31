#!/usr/bin/python

sensor1 = '/sys/devices/platform/coretemp.0/hwmon/hwmon1/temp2_input'
sensor2 = '/sys/devices/platform/coretemp.0/hwmon/hwmon1/temp3_input'
primary_fanfile = '/proc/acpi/ibm/fan'

import time


class fanOut(object):

    def __init__(self, fanfile):
        self.fanfile = fanfile

    def set_level(self, level):
        with open(self.fanfile, 'w') as f:
            f.write(level.outtext)


defaultFanOut = fanOut(primary_fanfile)


class tempSensor(object):

    def __init__(self, sensorFiles):
        self.sensorFiles = sensorFiles

    def get_temp(self):
        maxtemp = None
        for sensorpath in self.sensorFiles:
            with open(sensorpath, 'r') as f:
                content = f.read()
                temp = float(content) / 1000
                if temp > maxtemp:
                    maxtemp = temp
        return maxtemp

defaultTempSensor = tempSensor([sensor1, sensor2])


class fanLevel(object):
    def __init__(self, outtext, mintemp, maxtemp):
        # Validate
        if mintemp is not None is not maxtemp:
            if mintemp > maxtemp:
                raise Exception('Lower max than min')
        self.outtext = outtext
        self.mintemp = mintemp
        self.maxtemp = maxtemp

    def isTooHigh(self, temp):
        if self.maxtemp is None:
            return False
        return temp > self.maxtemp

    def isTooLow(self, temp):
        if self.mintemp is None:
            return False
        return temp < self.mintemp


class fanController(object):
    def __init__(self, fanOut, fanLevels, default=0):
        assert len(fanLevels)
        validateFanLevels(fanLevels)
        self.fanOut = fanOut
        self.fanLevels = fanLevels
        self.curIdx = default
        self.maxIdx = len(fanLevels) - 1

    @property
    def curLevel(self):
        return self.fanLevels[self.curIdx]

    def getLevel(self, idx):
        return self.fanLevels[idx]

    def find_desired_level(self, temp):
        curLevel = self.curLevel
        if curLevel.isTooHigh(temp) and self.curIdx < self.maxIdx:
            self.curIdx += 1
            self.find_desired_level(temp)

        elif curLevel.isTooLow(temp) and self.curIdx > 0:
            self.curIdx -= 1
            self.find_desired_level(temp)

    def update(self, temp):
        self.find_desired_level(temp)
        self.apply_level(self.curLevel)

    def apply_level(self, level):
        self.fanOut.set_level(level)


class fanLoop(object):
    def __init__(self, fanController, tempFunc):
        self.fanController = fanController
        self.tempFunc = tempFunc
        self.cycle()

    def getTemp(self):
        return self.tempFunc()

    def cycle(self):
        temp = self.getTemp()
        self.fanController.update(temp)


def validateFanLevels(fanLevels):
    for i in range(0, len(fanLevels) - 1):
        cur = fanLevels[i]
        nxt = fanLevels[i + 1]
        if cur.maxtemp < nxt.mintemp:
            raise Exception('Invalid temperatures')


fanlevels = [
    fanLevel('disable', None, 55),
    fanLevel('level 3', 45, 70),
    fanLevel('level 5', 65, 85),
    fanLevel('level 7', 75, None),
]


mainFanController = fanController(defaultFanOut, fanlevels)
mainFanLoop = fanLoop(mainFanController, defaultTempSensor.get_temp)

while True:
    mainFanLoop.cycle()
    time.sleep(3)
