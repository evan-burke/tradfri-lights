from sqlitelib import sqlitelib
import json
import os

# dev/debug:
from pprint import pprint


# purpose: quick way to get current states for all lights, and time since last update.
# to be run on command line - sudo python3 allstates.py

# todo: take lights as a list, insert dynamically into query.


# This is a little clunky, because the db needs to be accessed by root - sqlite gives error otherwise, even in read only mode.
# also not clear if this locks DB for HA? though query is super quick so... maybe not an issue.
# eh. I think I saw some odd behavior when testing this. not sure.


db_file = "/home/homeassistant/.homeassistant/home-assistant_v2.db"


# ----------------------------------------


def mireds_to_kelvin(mireds):
        return round(1000000 / mireds)


if os.geteuid() != 0:
    exit("You need to have root privileges to run this script.")


# use uri mode so we can do read only
db_uri = "file:" + db_file + "?mode=ro"

db = sqlitelib(db_file)

latest_states_query = """select datetime(s.last_updated,'localtime') as last_updated,
	 s.entity_id, s.state, s.attributes,
	strftime('%s','now') - strftime('%s', last_upd) as seconds_since_last_update
	from states s
	join (select entity_id, max(last_updated) as last_upd
		from states
		where entity_id in ('light.geo_desk','light.desk_lamp','light.lightstrip_2',
				'light.mon_left','light.mon_right','light.up_left','light.up_right')
		group by entity_id) l on s.entity_id=l.entity_id and s.last_updated = l.last_upd
	where s.entity_id in ('light.geo_desk','light.desk_lamp','light.lightstrip_2',
                                'light.mon_left','light.mon_right','light.up_left','light.up_right')
	and s.last_updated = last_upd;"""


data = db.execute(latest_states_query)


for n, i in enumerate(data):
	attrs = json.loads(i['attributes'])

	if 'color_temp' in attrs:
		color_temp_kelvin = mireds_to_kelvin(attrs['color_temp'])
		data[n]['color_temp_kelvin'] = color_temp_kelvin
	if 'brightness' in attrs:
		data[n]['brightness'] = attrs['brightness']
	# trim attrs from original dict, we don't need them anymore
	del data[n]['attributes']

pprint(data, indent=4)
