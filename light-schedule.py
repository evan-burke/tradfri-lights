import tradfri
import datetime
import argparse

#import json



devices = { 
	"office_table": 
		{ "entity_id": "light.tradfri_bulb_e26_ws_opal_980lm" },
	"geo_desk":
		{ "entity_id": "light.tradfri_bulb_e12_ws_opal_400lm_2" }
	}





debug=1

tradfri.transition(devices['geo_desk']['entity_id'], {"brightness": 92}, datetime.timedelta(minutes=1))


#transition(ent_id, {"color_temp": 2700}, datetime.timdelta(hours=2))

#tradfri.set_brightness(ent_id, 192)

