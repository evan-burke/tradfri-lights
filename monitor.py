

from tradfri import Tradfri


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


print("device, brightness, color_temp(k)")


import time
for _ in range(100):

	# this uses the old procedural version

	for i in devices:
		attrs = tradfri.get_attrs(devices[i]['entity_id'])
		print(i, attrs['brightness'], round(1000000/attrs['color_temp']), sep='\t')
	print()
	time.sleep(7)
	
	
