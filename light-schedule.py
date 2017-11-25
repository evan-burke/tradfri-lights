from tradfri import Tradfri
import datetime
import argparse

# used for 'transition' function
#import pytimeparse
import dateutil.parser


#import json

#Define your tradfri devices here by friendly name and HomeAssistant entity id.

devices = { 
	"office_table": { 
		"entity_id": "light.tradfri_bulb_e26_ws_opal_980lm"
	},

	"geo_desk": {
		"entity_id": "light.tradfri_bulb_e12_ws_opal_400lm_2"
	}
}

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

#subparser = parser.add_subparsers(help='zyx')
#parser_transition = subparser.add_parser('transition')

args = parser.parse_args()

# Most common actions:
acts = """
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
# This is not the right way to do it, because argparse will probably do a better job at this sort of thing. 
# Plus, delimiting values by '=' doesn't match the param format in argparse.

# example:
# python3 light-schedule.py geo_desk transition color_temp=3200 seconds=7 start_time=5:23

transition_supported_attrs = ['brightness','color_temp']
transition_supported_durations = ['second','seconds','minute','minutes','hour','hours']

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
		print('durval:', dur[1])
		if 'second' in dur_unit:
			dur_value = int(dur[1])
		elif 'minute' in dur_unit:
			dur_value = int(dur[1]) * 60
		elif 'hour' in dur_unit:
			dur_value = int(dur[1]) * 60 * 60
		print('durval2', dur_value)
		duration = datetime.timedelta(seconds=dur_value)

	# if present, parse start time
	try:
		if 'start_time' in params[2]:
			_p2 = params[2].replace(" ", "").split("=")
			print("params2:", params[2], "p2:",  _p2)
			start_time = dateutil.parser.parse(_p2[1])
	except:
		print("except blockq")
		start_time = None
	
	print("parsed values:")
	print(new_attr)
	print(duration)
	if start_time: print(start_time)

	return new_attr, duration, start_time	





from pprint import pprint
print("args:")
pprint(args)
print("")
print("params:")
print(args.params)
print("")

new_attr, duration, start_time = parse_transition_params(args.params)



device = Tradfri(devices[args.device]['entity_id'], debug=args.verbose)

#pprint(device.get_attrs())

func = getattr(device, args.action)
if args.action == 'transition':
	new_attr, duration, start_time = parse_transition_params(args.params)
	resp = func(new_attr, duration, start_time)

else:
	if args.params:
		if len(args.params) > 0:
			resp = func(args.params)
	else:
		resp = func()

if resp:
	pprint(resp)

#device.set_brightness(args.params)

#device.toggle()




#data = tradfri.get_attrs(devices['geo_desk']['entity_id'])
#print(data['brightness'], data['color_temp'])

















quit()

#tradfri.debug = 1

quit332 = """
tradfri.transition(devices['geo_desk']['entity_id'], {"brightness": 0}, datetime.timedelta(seconds=7))
tradfri.transition(devices['geo_desk']['entity_id'], {"brightness": 112}, datetime.timedelta(seconds=7))
"""


#transition(ent_id, {"color_temp": 2700}, datetime.timdelta(hours=2))

#tradfri.set_brightness(ent_id, 192)

