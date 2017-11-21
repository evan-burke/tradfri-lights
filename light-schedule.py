import tradfri
import datetime

import json

print("hello")


# light bulb id
ent_id = "light.tradfri_bulb_e26_ws_opal_980lm"

debug=1

#tradfri.transition(ent_id, {"brightness": 192}, datetime.timedelta(minutes=1))

#transition(ent_id, {"color_temp": 2700}, datetime.timdelta(hours=2))

#tradfri.set_brightness(ent_id, 192)

data3 = tradfri.get_bulb_state(ent_id)
print(data3)

from pprint import pprint

data = tradfri.apireq("states/" + ent_id, "get")
state = json.loads(data.text)
pprint(state)
