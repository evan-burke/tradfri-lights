import tradfri
import datetime
import argparse

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
parser.add_argument("--params", "-p", default=None, help="Parameters for the specified action, as a dict.")
parser.add_argument("--verbose", "-v", default=0, type=int, choices=[1,2], help="Increase verbosity of output.")
args = parser.parse_args()

from pprint import pprint
print("")
pprint(args)


data = tradfri.get_attrs(devices['geo_desk']['entity_id'])
print(data['brightness'], data['color_temp'])

















quit()

#tradfri.debug = 1

tradfri.transition(devices['geo_desk']['entity_id'], {"brightness": 0}, datetime.timedelta(seconds=7))
tradfri.transition(devices['geo_desk']['entity_id'], {"brightness": 112}, datetime.timedelta(seconds=7))



#transition(ent_id, {"color_temp": 2700}, datetime.timdelta(hours=2))

#tradfri.set_brightness(ent_id, 192)

