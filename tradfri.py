import requests
import json
import math
import time
import datetime

# HomeAssistant base API URL.
API_URL = "http://192.168.132.162:8123/api/"


debug = 0

# Min/max values for your light. These are for ikea TRADFRI white spectrum.
MIN_BRIGHTNESS = 0
MAX_BRIGHTNESS = 254
MIN_COLOR_TEMP_KELVIN = 2200
MAX_COLOR_TEMP_KELVIN = 4000

# Updating too fast can cause flickering. Recommended 0.1-0.2, not less than 0.1.
# Too high makes faster transitions stuttery as well, due to larger increases per step.
MIN_STEP_DURATION = datetime.timedelta(seconds=0.1)



def apireq(endpoint, req_type = "get", post_data = None):
    if req_type == "get":
        data = requests.get(API_URL + endpoint)
        if debug and data.status_code != 200: 
            print("http response: " + str(data.status_code), data.url,   sep="\n") #data.text,
        return data
    elif req_type == "post":
        if not post_data:
            print("error: post specified, but no post data passed")
            return 0
        else:
            if type(post_data) is dict:
                # convert to json
                post_data = json.dumps(post_data)
            data = requests.post(API_URL + endpoint, post_data)
            return data
    else:
        print("unsupported http type: ", req_type)
        return 0

def get_bulb_state(entity_id):
    """Low level function. Returns entire state array."""
    data = apireq("states/" + entity_id, "get")
    state = json.loads(data.text)
    return state


def get_attrs(entity_id):
    """ Returns 'attributes' component of light state - only if light is on."""
    state = get_bulb_state(entity_id)
    if state['state'] == 'on':
        attrs = state['attributes']
        return attrs
    else:
        print('light is not on; unable to retrieve attributes')
        return False


def get_temp_kelvin(entity_id):
    """ Retrieves current bulb state and converts 'mireds' to kelvin.
        Note there is some rounding/approximation going on somewhere
        in the chain, which means returned value will almost never
        equal the value set via the API."""
    attrs = get_attrs(entity_id)
    if attrs:
        mireds = attrs['color_temp']
        return mireds_to_kelvin(mireds)


def mireds_to_kelvin(mireds):
    kelvin = round(1000000 / mireds)
    return kelvin


def get_brightness(entity_id):
    """ Gets current brightness, 0-255."""
    attrs = get_attrs(entity_id)
    if attrs:
        return attrs['brightness']


def check_if_on(entity_id):
    state = get_bulb_state(entity_id)
    if state['state'] == 'on':
        return True
    else:
        return False
    

def set_bulb_attributes(entity_id = None, attrs = None):
    """ Low-level function.
    Entity_id is the entity_id string for the light to update.
    Attrs is a dict containing attr(s) to set. e.g.: {'brightness': 92}
    
    Function can either be called with both params, or just attrs, if that dict
        contains an entity id as well, e.g.:
        {'entity_id': 'light.tradfri_bulb_e26_ws_opal_980lm', 'brightness': 92}
    """
    
    if not entity_id and not "entity_id" in attrs:
        print("error: function needs an entity_id as input somewhere")
        time.sleep(2)
        return 0
    
    if entity_id and attrs: 
        # create new dict containing both. may require python 3.5+
        attrs = {"entity_id": entity_id }

    data = apireq("services/light/turn_on", "post", attrs)
    # this doesn't usually return anyything other than http response code, but return just in case. 
    # This is a 'requests' response. 
    return data


def set_color(entity_id, kelvin):
    """ Sets color temperature of the light. 
    May allow you to set color temp outside of supported range of bulb: some bulbs
    do not reutrn an error, instead just setting bulb to closest supported temp."""
    
    data = set_bulb_attributes(entity_id, {"kelvin": kelvin})
    return data


def set_brightness(entity_id, brightness):
    """ Sets light brightness, in range 0-254. 0 is off. """
                
    data = set_bulb_attributes(entity_id, {"brightness": brightness })
    return data


def sanity_check_values(new_attr):
    if "brightness" in new_attr:
        if new_attr['brightness'] > MAX_BRIGHTNESS:
            new_attr['brightness'] = MAX_BRIGHTNESS
        elif new_attr['brightness'] < MIN_BRIGHTNESS:
            new_attr['brightness'] = MIN_BRIGHTNESS
            
    if "color_temp" in new_attr:
        if new_attr['color_temp'] < MIN_COLOR_TEMP_KELVIN:
            new_attr['color_temp'] = MIN_COLOR_TEMP_KELVIN
        elif new_attr['color_temp'] > MAX_COLOR_TEMP_KELVIN:
            new_attr['color_temp'] = MAX_COLOR_TEMP_KELVIN
    
    return new_attr


def transition(entity_id, new_attr, duration, start_time=None):
    """ Highest-level function. Initiates a transition for the given
        entity_id, based on the target values contained in new_attr,
        and the 'duration' which is a timedelta.
        If start_time is not set, start immediately. 
        Otherwise, sleeps until start_time.
        
        """
    plan = plan_transition(entity_id, new_attr, duration, start_time)
    
    if not plan:
        return 0
    
    if debug > 0: pprint(plan['details'])
    
    plan_start = plan['plan'][0]['step_start_time']
    time_until_start = plan_start - datetime.datetime.now()
    
    transition_type = plan['details']['transition_type']
    
    def apply_attrs(entity_id, transition_type, attrs):
        if transition_type == "brightness":
            data = set_brightness(entity_id, attrs)
        elif transition_type == "color_temp":
            data = set_color(entity_id, attrs)
        return data
    
    print("time until start", time_until_start)
    time.sleep(time_until_start.total_seconds() - 0.1)
    
    step_sleep = MIN_STEP_DURATION.total_seconds()

    if debug > 0: print("starting transition")
    
    for n, i in enumerate(plan['plan']):
        if debug > 0: print(str(n)+", ", end="")
        while datetime.datetime.now() < i['step_start_time']:
            time.sleep(step_sleep)
        
        apply_attrs(entity_id, transition_type, i[transition_type])
        time.sleep(step_sleep)
        
        if n+1 >= plan['details']['steps']:
            print("\n", i)
        
    if debug > 0: print("transition completed after", n+1, "steps")


def plan_transition(entity_id, new_attr, duration, start_time=None):
    """ x """
    new_attr = sanity_check_values(new_attr)
    
    current_attrs = get_attrs(entity_id)
    # ^ is False if bulb is off.
    if not current_attrs:
        # then we can only transition if the attribute to change is 'brightness'.
        if "brightness" not in new_attr:
            print('error: transition from off state only supported for "brightness" value')
            return 0
        else:
            current_attrs = {'brightness': 0}

    if not start_time:
        start_time = datetime.datetime.now() + datetime.timedelta(seconds=0.5)
        
    steps = calculate_transition_steps(entity_id, current_attrs, new_attr, duration)
    
    if not steps:
        return 0
    
    # loop init
    transition_type = list(new_attr)[0]   
    iter_time = start_time
    iter_value = current_attrs[transition_type]
    transition_steps=[]
    for i in range(steps['steps']):
        iter_value += steps['step_change'] # increment before
        idict = { transition_type: round(iter_value,3),
                 'step_start_time': iter_time,
                 'step_number': i
                }
        transition_steps.append(idict)
        iter_time += steps['step_duration'] # increment after

    details = steps
    details['start_time'] = start_time
    details['entity_id'] = entity_id
    details['transition_type'] = transition_type
    details['start_value'] = current_attrs[transition_type]
    details['target_value'] = new_attr[transition_type]
    transition_plan = { "details": steps, "plan": transition_steps}
    return transition_plan
    

def calculate_transition_steps(entity_id, current_attrs, new_attr, duration):
    """ Used in transition() function. 
        Given current state (current_attrs), desired state (new_attr) and length
        of time to transition to it (duration), calculates how many steps to take.
        Returns dict of:
            steps (int)
            step_duration (float)
            step_change (float)
        This does not need to be particularly precise for color temp, because
        there is imprecision somewhere in the chain between homeassistant
        and the bulb itself, which results in ~1% inaccuracy in response values.
        """
    
    
    def calculate_steps_by_granularity(current_attrs, new_attr):  
        ## Calculate transition steps with respect to granularity of data available. 
        
        # These set the properties for various transition types. 
        # Both of these start at 1. Brightness does not include '0' / off value.
        # Based on ikea tradfri white spectrum. 
        properties = {"brightness": {"granularity": 254, "range": 254}, 
                      "color_temp": {"granularity": 205, "range": 1800}
                      }
        
        for key in new_attr:
            if key == 'color_temp':
                #convert to kelvin & store
                kelvin = mireds_to_kelvin(current_attrs['color_temp'])
                current_attrs['color_temp'] = kelvin

            # skip if current state and transition state are equal:
            if new_attr[key] == current_attrs[key]:
                if debug > 0: print("current value and new value are already equal")
                return 0, 0

            # calculate amount of change, as % of total range. 
            total_change = new_attr[key] - current_attrs[key]
            change_amt = abs(total_change / properties[key]['range'])

            # skip if less than minimum granularity
            if change_amt < (1/properties[key]['granularity']):
                if debug > 0: print("current value and new value are almost identical")
                return 0, 0

            # calculate # of steps to take
            steps = math.floor(change_amt * properties[key]['granularity'])

            if debug > 0:
                print("type:", key, "\tcurrent:", current_attrs[key], \
                     "\tdesired:", new_attr[key], "\tsteps:", steps)

            # this can happen due to approximation in the bulb/tradfri somewhere. 
            if steps > properties[key]['granularity']:
                steps = properties[key]['granularity']

            return steps, total_change
    
    
    def calculate_steps_by_time(steps, total_change, duration):
        ## Calculate transition steps / step duration based on time.
    
        # minimum steps we can do in the specified transition duration (don't transition too fast):
        duration_min_steps = math.ceil(duration / MIN_STEP_DURATION)
        if debug > 0: print('duration min steps', duration_min_steps)

        if duration_min_steps < steps:
            steps = duration_min_steps
        
        step_change = total_change / steps
        step_duration = duration / steps
        
        return steps, step_duration, step_change
    
    
    steps, total_change = calculate_steps_by_granularity(current_attrs, new_attr)
    if steps and total_change:
        steps, step_duration, step_change = calculate_steps_by_time(steps, total_change, duration)
        return {"steps": steps, "step_duration": step_duration, "step_change": step_change}
    else:
        return 0
    

def lightswitch(entity_id, power = True):
    """ turns light on if power=true, off if power=false."""
    
    attrs = {'entity_id': entity_id }
    if power:
        data = apireq("services/light/turn_on", "post", attrs)
    else:
        data = apireq("services/light/turn_off", "post", attrs)
    
