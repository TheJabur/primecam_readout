"""
	set_still_LD_client.py
	Written by ZBH, 9/28/2021
	Modeled off of Nick's set_still_LD.py and my set_still_SD_client.py

	Client script to turn the still heater on the LS372 on and off

	---------------------------------------------------------
	Operation:
	Run from the command line while ssh'd into Gamow.

	Example - "python3 set_still_LD_client.py on -p 20"
	This will turn on the still heater and set it to 20% power.

	Arguments:
		mode (str) - required argument, accepts "on" or "off"
		--power or -p (float) - optional argument,
                                        sets the still power percentage,
					defaults to 25.0% from 20220901 LD load curve
"""

import argparse
from ocs.ocs_client import OCSClient

# Parser for collecting the necessary arguments
parser = argparse.ArgumentParser()
parser.add_argument("mode", help="Whether to turn the still heater on or off",
					type=str, choices=['on','off'])
parser.add_argument("-p", "--power", help="The still heater power to set", type=float)
args = parser.parse_args()

argument = args.mode
power = 25.0 # Default to a standard LD value from load curve on 20220901 - may be slightly high

#Check if a different power given in optional arg
if args.power:
	power = args.power

# Setting up the Lakeshore 372 client
# ls372 = OCSClient('LSA23DG',args=[])

# Setting the still mode to Still in case it wasn't already
# ls372.set_output_mode(heater='still',mode='Still')

# Turning the still heater on in case it wasn't already
# ls372.set_heater_range(heater='still',range='On',wait=1)

# Turning still on or off
print('Setting still power {}'.format(argument))
if argument == 'on':
	print('On to ' + str(power) + '% power')
	# ls372.set_still_output(output=power)
if argument == 'off':
	print("Off to 0% power")
	# ls372.set_still_output(output=0.0)
	print("Turning off the still heater")
	# ls372.set_heater_range(heater='still',range='off',wait=1)

# Checking that the still output is set correctly
# ls372.get_still_output()
# result = ls372.get_still_output.status()
# print(result)

print("The still heater output has been set.")


