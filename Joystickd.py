#!/usr/bin/env python3
#############################################################################
# Filename      : Joystickd.py
# Description   : Using smbus on Libreboard without needing to install "ADCDevice.py" with joystick
# auther        : Alonzo Ortiz-Sanchez
# modification  : 2023/02/06
# gpio physical : 3, 5, 8
# gpio offset   : 5, 4, 91
# gpio BCM/RPI  : SDA1, SCL1, GPIO_14
# gpio libre    : GPIOAO_5, GPIOAO_4, GPIOX_12
# chip          : gpiochip1
#############################################################################
from multiprocessing import Process
import smbus, time, gpiod

# -------------------- #
# Defining class START #
# -------------------- #

# Re-made the class from "ADCDevice" and made it more friendlier to read
class SimpleADC():
	# Preparing the setup for hooking up the device
	def __init__(self, addr, cmd=0, chnList = []):
		"""
		A more than complicated startup to ensure the ADC device is ready to be used
		"""
		self.cmd = cmd
		self.addr = addr
		self.chnRead = chnList
		self.ready = False

		# Based on the two known devices given from the kit, I will define the channels

		# First device is for PCF8591
		if self.addr == 0x48 and (len(self.chnRead) == 0 or self.cmd == 0):
			self.cmd = 0x40 # Appearantly this is the default one
			self.chnRead = [self.cmd+0, self.cmd+1, self.cmd+2, self.cmd+3] # It has 4 ADC input pints, where the chn are literal (so simple addition works)
		# Last device is for ADS7830
		elif self.addr == 0x4b and (len(self.chnRead) == 0 or self.cmd == 0):
			self.cmd = 0x84 # Appearantly this is the default one
			for chn in range(0, 8): # Made a loop to simplify code
				self.chnRead.append(0|(((chn<<2 | chn>>1)&0x07)<<4)) # A very fancy math equation is used here
		elif len(self.chnRead) == 0 or self.cmd == 0:
			Input("Did not a known address from the Freenovo kit.\nProceed? If not, Ctrl+C")
		else:
			print("Custom input given received well")

		# Initiating SMbus so we can properely use I2C
		self.bus = smbus.SMBus(1)
		self.useAddr(self.addr)
		self.ready = True
	
	# In case we mest up, or wish to change the device
	def useAddr(self, addr):
		"""
		Checks if the address for the device exists
		"""
		try:
			self.bus.write_byte(addr, self.cmd) # We sent a cmd to the given address
			print("Device has been found on address: 0x%x"%(addr))
			self.addr = addr
			return True
		except:
			print("It has not been found with address: 0x%x"%(addr))
			return False
	
	# We read from devices through channels, and for each device, it can be unique
	def getRead(self, chnIndex):
		"""
		Reads from the ADC via the index given
		"""
		value = self.bus.read_byte_data(self.addr, self.chnRead[chnIndex])
		return value

	# See if it exists
	def getReady(self):
		return self.ready

	# We write to the device by a DAC (essentially Digital -> Analog signal) value.
	def putWrite(self, dac):
		"""
		Writes to the ADC via its cmd
		"""
		self.bus.write_byte_data(self.addr, self.cmd, dac) # By using default cmd, we are writing to the device
	
	# To safely close the smbus
	def close(self):
		"""
		Closes the bus from SMbus
		"""
		self.bus.close()


# ------------------ #
# Defining class END #
# ------------------ #

# Defining parameters
addr = 0x4b     # My chip comes with 0x4b when plugged in, setup (wires included)
adc = SimpleADC(addr) # When I ran `sudo i2cdetect -y 1`
chip1 = gpiod.Chip("gpiochip1")
pushRead = chip1.get_line(91)

# Functions
def setup():
	"""
        This will initialize the variables used throughout the program.
        Am new to gpio so this is a bit more commentated than usual
        """
	global pushRead, adc
	assert(adc.getReady())
	pushRead.request(consumer='Used to change the frequency of the LED via semi analog signals.',
			type=gpiod.LINE_REQ_DIR_IN, #Declaring that it will make cu>
			default_vals=[0],
			flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP) # We want the current to stay consistent, so we add a flag for that
	print("Program Started")

def run():
	global adc, pushRead
	while True:
		val_Z = "On" if not pushRead.get_value() else "Off"
		val_Y = adc.getRead(0)
		val_X = adc.getRead(1)
		print(f"X axis & Y axis: ({val_X},{val_Y}) | Z axis state: {val_Z}")
		time.sleep(0.01)

def halt():
	"""
	We safely clean up, and stop using any gpio's currently used by the system
	"""
	global chip1, pushRead
	print("\rProgram has ended, setting pins back to initial state")
	if pushRead.active_state():
			pushRead.release()
	chip1.close()
	print("Succesfully terminated")

if __name__ == "__main__":
	"""
	Where our program execution starts
	"""
	print("Program is starting")
	setup()
	try:		# Running forever
		run()
	except KeyboardInterrupt:	# Can only be stopped by Ctrl+C
		adc.close()
		halt()
