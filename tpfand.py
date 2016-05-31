#!/usr/bin/python

sensor1 = '/sys/devices/platform/coretemp.0/hwmon/hwmon1/temp2_input'
sensor2 = '/sys/devices/platform/coretemp.0/hwmon/hwmon1/temp3_input'
fanfile = '/proc/acpi/ibm/fan'

import time

class fanOut(object):
	def setactive(self):
		with open(self.fanfile, 'w') as f:
			f.write(self.output)

class defaultFanOut(fanOut):
	fanfile = fanfile

class tempSensor(object):
	def __init__(self, sensorFiles):
		self.sensorFiles = sensorFiles

	def gettemp(self):
		maxtemp = None
		for sensorpath in self.sensorFiles:
			with open(sensorpath, 'r') as f:
				content = f.read()
				temp = float(content) / 1000
				if temp > maxtemp:
					maxtemp = temp
		return maxtemp

defaultTempSensor = tempSensor([sensor1, sensor2])

class fanLevel(defaultFanOut):
	def __init__(self, output, mintemp, maxtemp):
		# Validate
		if mintemp is not None is not maxtemp:
			if mintemp > maxtemp:
				raise Exception('Lower max than min')
		self.output = output
		self.mintemp = mintemp
		self.maxtemp = maxtemp
		self.isactive = False

	def markactive(self):
		self.isactive = True

	def markinactive(self):
		self.isactive = False

	def setactive(self):
		super(self.__class__, self).setactive()
		self.markactive()

	def reapply(self):
		super(self.__class__, self).setactive()

	# Going to be lazy and use these
	def isTooHigh(self, temp):
		if self.maxtemp is None:
			return False
		return temp > self.maxtemp

	def isTooLow(self, temp):
		return temp < self.mintemp

class fanController(object):
	def __init__(self, fanLevels, default = 0):
		assert len(fanLevels) > 0
		validateFanLevels(fanLevels)
		self.fanLevels = fanLevels
		self.curIdx = default
		self.maxIdx = len(fanLevels) - 1
		self.curLevel.setactive()


	@property
	def curLevel(self):
		return self.fanLevels[self.curIdx]

	def getLevel(self, idx):
		return self.fanLevels[idx]

	def process(self, temp):
		curLevel = self.curLevel
		if curLevel.isTooHigh(temp) and self.curIdx < self.maxIdx:
			self.curIdx += 1
			self.process(temp)

		elif curLevel.isTooLow(temp) and self.curIdx > 0:
			self.curIdx -= 1
			self.process(temp)

	def update(self, temp):
		oldIdx = self.curIdx
		self.process(temp)
		newIdx = self.curIdx

		if oldIdx == newIdx:
			self.curLevel.reapply()

		else:
			oldLevel = self.getLevel(oldIdx)
			oldLevel.markinactive()
			self.curLevel.setactive()

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
	fanLevel('level 3', 50, 70),
	fanLevel('level 5', 65, 85),
	fanLevel('level 7', 75, None),
]


mainFanController = fanController(fanlevels)
mainFanLoop = fanLoop(mainFanController, defaultTempSensor.gettemp)

while True:
	mainFanLoop.cycle()
	time.sleep(3)
