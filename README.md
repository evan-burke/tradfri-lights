# tradfri-lights
'f.lux'-like app for Ikea Tradfri white spectrum smart bulbs and gateway. 


Files:

**tradfri.py** is the main package handling light control & transition logic. 


**light-schedule.py** is a wrapper for tradfri.py which provides command line argument parsing, and defines a mapping of friendly device names to HomeAssistant IDs. Cronjobs will call this script to initiate state transitions.


**lights-auto.py** is a utility run on your primary Windows machine in the office where lights are located. During daytime, it will transition lights to 'daytime' state based on mouse/keyboard activity. This is required because lights can't transition state when there's no power to them, so turning power on to the lights won't automatically set them in a state which was sent to the hub while they were off.

**automations.yaml** is an example HomeAssistant automation triggered by lights-auto.py.


**monitor.py** is a debugging script to show details of state transitions as they happen. 




