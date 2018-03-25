from tradfri import Tradfri
import datetime
import argparse

# used for 'transition' function
#import pytimeparse
import dateutil.parser
import tradfri_cfg


### Define your tradfri devices here by friendly name and HomeAssistant entity id.

devices = tradfri_cfg.devices

# moving this to tradfri_cfg instead
old_devices = { 
	"office_table": { 
		"entity_id": "light.office_table"
	},

	"geo_desk": {
		"entity_id": "light.geo_desk"
	},

	"desk_lamp": {
		"entity_id": "light.desk_lamp"
	},

	"office_uplight": {
		"entity_id": "light.floor_uplight"
	},

	"mon_right": {
		"entity_id": "light.monitor_right"
	},

	"mon_left": {
		"entity_id": "light.monitor_left"
	},

	"mon_group": {
		"entity_id": "light.monitor"
	},


}



transition_supported_attrs = ['brightness','color_temp']
transition_supported_durations = ['second','seconds','minute','minutes','hour','hours']


# Debug switch for this script. separate from tradfri.py debug switch.
debug = 0


# --------------

# Script

parser = argparse.ArgumentParser(conflict_handler='resolve')

# args:
# device friendly name
# action
# action params (dict)

parser.add_argument("device", help="Friendly name of the device to update.")
parser.add_argument("action", help="Action to take on the specified device. See tradfri.py for supported actions.")
parser.add_argument("params", nargs='*', default=None, help="Parameters for the specified action.")
parser.add_argument("--verbose", "-v", default=0, type=int, choices=[1,2], help="Increase verbosity of output.")
args = parser.parse_args()

# Most common actions:
actions = """
check_if_on()
get_temp_kelvin()
get_brightness()
set_color(kelvin)
set_brightness(brightness)
transition(new_attr, duration, start_time=None)
lightswitch(power = True)
toggle()
"""

# Transition is the special case. 
# Need to parse new_attr, duration, and start_time.
# This is... not the right way to do it, because argparse will probably do a better job at this sort of thing. 
# Plus, delimiting values by '=' doesn't match the param format in argparse.

# example:
# python3 light-schedule.py geo_desk transition color_temp=3200 seconds=7 start_time=5:23


def parse_transition_params(params):
	# parse new setting / attr:
	attr = params[0].replace(" ", "").split("=")
	if attr[0] not in transition_supported_attrs:
		print("error: attribute of", attr[0], "not supported. supported attributes:", transition_supported_attrs)
		quit()
	else:
		new_attr = { attr[0]: int(attr[1]) }
		#value = attr[1]


	# parse transition duration
	dur = params[1].replace(" ", "").split("=")
	if dur[0] not in transition_supported_durations:
		print("error: duration unit of", dur[0], "not supported. supported durations:", transition_supported_durations)
		quit()
	else:
		dur_unit = dur[0]
		if 'second' in dur_unit:
			dur_value = int(dur[1])
		elif 'minute' in dur_unit:
			dur_value = int(dur[1]) * 60
		elif 'hour' in dur_unit:
			dur_value = int(dur[1]) * 60 * 60
		duration = datetime.timedelta(seconds=dur_value)

	# if present, parse start time
	try:
		if 'start_time' in params[2]:
			_p2 = params[2].replace(" ", "").split("=")
			#print("params2:", params[2], "p2:",  _p2)
			start_time = dateutil.parser.parse(_p2[1])
	except:
		#print("except block for start_time")
		start_time = None
	
	if debug:
		print("parsed values:")
		print(new_attr)
		print(duration)
		if start_time: print(start_time)

	return new_attr, duration, start_time	




if debug:
	from pprint import pprint
	print("args:")
	pprint(args)
	print("")
	if args.params:
		print("params:")
		print(args.params)
		print("")

	print("creating instance for friendly name:", args.device, "id", devices[args.device]['entity_id'])

device = Tradfri(devices[args.device]['entity_id'], debug=args.verbose)


func = getattr(device, args.action)

if args.action == 'transition':
	#special case
	new_attr, duration, start_time = parse_transition_params(args.params)
	resp = func(new_attr, duration, start_time)

elif args.action == 'lightswitch':
	# convert to bool
	test_arg = args.params[0].lower()
	if test_arg == 'true' or test_arg == '1':
		func_input = True
	elif test_arg == 'false' or test_arg == '0':
		func_input = False
	else:
		func_input = None
		# lightswitch() function defaults to True if no input. 
	
	resp = func(func_input)

elif args.action in ['set_brightness','set_color','mireds_to_kelvin','kelvin_to_mireds']:
	resp = func(int(args.params[0]))

# Above are just the commonly used functions.
# There's nothing to stop user from calling a lower-level/internal function here, but args won't be used, so some may fail.
else:
	resp = func()

if resp:
	from pprint import pprint
	pprint(resp)
















