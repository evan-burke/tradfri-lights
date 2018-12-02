""" Light automation module for IKEA Tradfri devices via HomeAssistant."""

import configparser
import datetime
import json
import math
import time
from pprint import pprint
import requests


# Welp. I may have needlessly rewritten this - https://home-assistant.io/components/switch.flux/
# Though - it isn't perfect anyway.
#   - https://community.home-assistant.io/t/improving-the-fluxer/23729


# HomeAssistant base API URL.
# API_URL = "http://192.168.132.162:8123/api/"
CONFIG_FILENAME = "tradfri.conf"

# Min/max values for your light. These are for ikea TRADFRI white spectrum.
MIN_BRIGHTNESS = 0
MAX_BRIGHTNESS = 254
MIN_COLOR_TEMP_KELVIN = 2200
MAX_COLOR_TEMP_KELVIN = 4000

# Updating too fast can cause flickering. Recommended 0.1-0.2, not less than 0.1.
# Too high makes faster transitions stuttery as well, due to larger increases per step.
# If HomeAssistant is slower to respond than this, this value
#   may be significantly faster than actual min step duration.
MIN_STEP_DURATION = datetime.timedelta(seconds=0.1)


class Tradfri(object):
    """ One class per individual light. """

    def __init__(self, device_name, debug=0):
        # get config
        self.config = configparser.ConfigParser()
        _ = self.config.read(CONFIG_FILENAME)
        self.api_url = self.config["tradfri"]["api_url"]

        self.entity_id = self.get_entity(device_name)
        self.debug = debug
        self.state = self.get_state()
        if self.state["state"] == "on":
            self.attrs = state["attributes"]
        else:
            self.attrs = {}

        try:
            if "Entity not found" in self.state["message"]:
                errstr = "Error creating instance: " + self.state["message"]
                print(errstr)
                raise Exception(errstr)
        except KeyError:
            # if there's no 'message', call probably succeeded
            pass

    def get_entity(self, device_name):
        """ Try to get the entity ID for the given device name. """

        # Check if it matches anything in the device map.
        device_map = json.loads(self.config["tradfri"]["device_map"])

        if device_name in device_map:
            return device_map["device_name"]

        # Else, just try prepending "light" to the entity name.
        return "light." + device_name

    def apireq(self, endpoint, req_type="get", post_data=None):
        """ Make an API request aginst HomeAssistant. """

        def handle_errors(data):
            if self.debug and data.status_code != 200:
                print(
                    "http response: " + str(data.status_code), data.url, sep="\n"
                )  # data.text,
            if str(data.status_code)[0] in ["4", "5"]:
                errstr = (
                    "fatal error from API. status: "
                    + str(data.status_code)
                    + " response text: "
                    + data.text
                )
                raise Exception(errstr)

        if req_type == "get":
            data = requests.get(self.api_url + endpoint)
            handle_errors(data)
            return data
        elif req_type == "post":
            if not post_data:
                print("error: post specified, but no post data passed")
                return 0
            else:
                if type(post_data) is dict:
                    # convert to json
                    post_data = json.dumps(post_data)
                data = requests.post(self.api_url + endpoint, post_data)
                handle_errors(data)
                return data
        else:
            print("unsupported http type: ", req_type)
            return 0

    def get_state(self):
        """Low level function. Returns entire state array."""
        data = self.apireq("states/" + self.entity_id, "get")
        self.state = json.loads(data.text)
        return self.state

    def get_attrs(self):
        """ Returns 'attributes' component of light state - only if light is on."""
        state = self.get_state()
        if state["state"] == "on":
            self.attrs = state["attributes"]
            self.attrs["kelvin"] = self.mireds_to_kelvin(self.attrs["color_temp"])
            return self.attrs
        else:
            print(
                datetime.datetime.now(),
                "\tlight is not on; unable to retrieve attributes",
            )
            return False

    def check_if_on(self):
        state = self.get_state()
        return bool(state["state"] == "on")

    def get_temp_kelvin(self):
        """ Retrieves current bulb state and converts 'mireds' to kelvin.
            Note there is some rounding/approximation going on somewhere
            in the chain, which means returned value will almost never
            equal the value set via the API."""
        attrs = self.get_attrs()
        if attrs:
            mireds = attrs["color_temp"]
            return self.mireds_to_kelvin(mireds)

    def get_color(self):
        # alias because this is more consistent with get_brightness() function name
        return self.get_temp_kelvin()

    @staticmethod
    def mireds_to_kelvin(mireds):
        return round(1000000 / mireds)

    @staticmethod
    def kelvin_to_mireds(kelvin):
        # yep, same function.
        return self.mireds_to_kelvin(kelvin)

    def get_brightness(self):
        """ Gets current brightness, 0-255."""
        attrs = self.get_attrs()
        if attrs:
            return attrs["brightness"]

    def set_attributes(self, attrs):
        """ Low-level function.
        Attrs is a dict containing attr(s) to set. e.g.: {'brightness': 92}
        """

        if self.entity_id not in attrs:
            # add entity_id to attrs
            attrs["entity_id"] = self.entity_id
            if self.debug > 1:
                print("set_attributes() attrs:", attrs)

        data = self.apireq("services/light/turn_on", "post", attrs)
        # this doesn't usually return anyything other than http response code,
        # but return just in case.
        # This is a 'requests' response.
        return data

    def set_color(self, kelvin):
        """ Sets color temperature of the light. 
        May allow you to set color temp outside of supported range of bulb: some bulbs
        do not reutrn an error, instead just setting bulb to closest supported temp."""

        data = self.set_attributes({"kelvin": kelvin})
        return data

    def set_brightness(self, brightness):
        """ Sets light brightness, in range 0-254. 0 is off. """

        data = self.set_attributes({"brightness": brightness})
        return data

    @staticmethod
    def sanity_check_values(new_attr):
        if "brightness" in new_attr:
            if new_attr["brightness"] > MAX_BRIGHTNESS:
                new_attr["brightness"] = MAX_BRIGHTNESS
            elif new_attr["brightness"] < MIN_BRIGHTNESS:
                new_attr["brightness"] = MIN_BRIGHTNESS

        if "color_temp" in new_attr:
            if new_attr["color_temp"] < MIN_COLOR_TEMP_KELVIN:
                new_attr["color_temp"] = MIN_COLOR_TEMP_KELVIN
            elif new_attr["color_temp"] > MAX_COLOR_TEMP_KELVIN:
                new_attr["color_temp"] = MAX_COLOR_TEMP_KELVIN

        return new_attr

    def transition(self, new_attr, duration, start_time=None):
        """ Highest-level function. Initiates a transition for the given
            entity_id, based on the target values contained in new_attr,
            and the 'duration' which is a timedelta.
            If start_time is not set, start immediately.
            Otherwise, sleeps until start_time.
            """

        plan = self.plan_transition(new_attr, duration, start_time)

        if not plan:
            return 0

        self.execute_transition(plan)

    def plan_transition(
        self,
        new_attr,
        duration=None,
        time_per_step=None,
        start_time=None,
        start_attr=None,
    ):
        """ new_attr is a single-item dict containing type of attribute & new value,
                e.g., {"brightness": 0}
            duration is a timedelta, as is time_per_step. One or the other must be set.
                If both are set, uses 'duration'.
            start_time is a datetime.
            start_attrs will define the starting attributes to use;
                if not set, this will start from current attributes.

        ### TODO: implment time_per_step

        """
        new_attr = self.sanity_check_values(new_attr)

        if duration is None and time_per_step is None:
            raise Exception(
                "Error: plan_transition() requires either 'duration' or 'time_per_step' to be set"
            )

        if start_attr:
            current_attrs = start_attr
        else:
            # get actuals
            current_attrs = self.get_attrs()
            # ^ is False if bulb is off.
            if not current_attrs:
                # then we can only transition if the attribute to change is 'brightness'.
                if "brightness" not in new_attr:
                    print(
                        datetime.datetime.now(),
                        '\terror: transition from off state only supported for "brightness" value',
                    )
                    return 0
                else:
                    current_attrs = {"brightness": 0}

        if not start_time:
            start_time = datetime.datetime.now() + datetime.timedelta(seconds=0.5)

        steps = self.calculate_transition_steps(current_attrs, new_attr, duration)

        if not steps:
            return 0

        # loop init
        transition_type = list(new_attr)[0]
        iter_time = start_time
        iter_value = current_attrs[transition_type]
        transition_steps = []
        for i in range(steps["steps"]):
            iter_value += steps["step_change"]  # increment before
            idict = {
                transition_type: round(iter_value, 3),
                "step_start_time": iter_time,
                "step_number": i,
            }
            transition_steps.append(idict)
            iter_time += steps["step_duration"]  # increment after

        details = steps
        details["start_time"] = start_time
        details["entity_id"] = self.entity_id
        details["transition_type"] = transition_type
        details["start_value"] = current_attrs[transition_type]
        details["target_value"] = new_attr[transition_type]
        transition_plan = {"details": steps, "plan": transition_steps}
        return transition_plan

    def calculate_transition_steps(
        self, current_attrs, new_attr, duration=None, time_per_step=None
    ):
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
            # That is, if there are only 254 brightness levels available, we can't do 300 steps.

            # These set the properties for various transition types.
            # Both of these start at 1. Brightness does not include '0' / off value.
            # Based on ikea tradfri white spectrum.
            properties = {
                "brightness": {"granularity": 254, "range": 254},
                "color_temp": {"granularity": 205, "range": 1800},
            }

            for key in new_attr:
                if key == "color_temp":
                    # convert to kelvin & store
                    kelvin = self.mireds_to_kelvin(current_attrs["color_temp"])
                    current_attrs["color_temp"] = kelvin

                # skip if current state and transition state are equal:
                if new_attr[key] == current_attrs[key]:
                    if self.debug > 0:
                        print("current value and new value are already equal")
                    return 0, 0

                # calculate amount of change, as % of total range.
                total_change = new_attr[key] - current_attrs[key]
                change_amt = abs(total_change / properties[key]["range"])

                # skip if less than minimum granularity
                if change_amt < (1 / properties[key]["granularity"]):
                    if self.debug > 0:
                        print("current value and new value are almost identical")
                    return 0, 0

                # calculate # of steps to take
                steps = math.floor(change_amt * properties[key]["granularity"])

                if self.debug > 0:
                    print(
                        "type:",
                        key,
                        "\tcurrent:",
                        current_attrs[key],
                        "\tdesired:",
                        new_attr[key],
                        "\tsteps:",
                        steps,
                    )

                # this can happen due to approximation in the bulb/tradfri somewhere.
                if steps > properties[key]["granularity"]:
                    steps = properties[key]["granularity"]

                return steps, total_change

        def calculate_steps_by_time(
            steps, total_change, duration=None, time_per_step=None
        ):
            ## Calculate transition steps / step duration based on time.
            # May further reduce # of steps for short duration transitions.

            ## one of 'duration' or 'time_per_step' needs to be set.
            # if both are set, uses duration.

            if duration:
                # minimum steps we can do in the specified transition duration (don't transition too fast):
                duration_min_steps = math.ceil(duration / MIN_STEP_DURATION)
                if self.debug > 0:
                    print("duration min steps", duration_min_steps)

                if duration_min_steps < steps:
                    steps = duration_min_steps

                step_duration = duration / steps

            elif time_per_step:
                step_duration = time_per_step

            step_change = total_change / steps
            return steps, step_duration, step_change

        steps, total_change = calculate_steps_by_granularity(current_attrs, new_attr)
        if steps and total_change:
            steps, step_duration, step_change = calculate_steps_by_time(
                steps, total_change, duration, time_per_step
            )
            return {
                "steps": steps,
                "step_duration": step_duration,
                "step_change": step_change,
            }
        else:
            return 0

    def execute_transition(self, plan):
        """Runs the transition specified by 'plan'."""

        if self.debug > 0:
            pprint(plan["details"])

        plan_start = plan["plan"][0]["step_start_time"]
        time_until_start = plan_start - datetime.datetime.now()

        transition_type = plan["details"]["transition_type"]

        def apply_attrs(transition_type, attrs):
            if transition_type == "brightness":
                data = self.set_brightness(attrs)
            elif transition_type == "color_temp":
                data = self.set_color(attrs)
            return data

        if (
            time_until_start.total_seconds() > 0
        ):  # only attempt to sleep for a positive value
            # wait until start time
            if self.debug > 0:
                print("time until start", time_until_start)
            time.sleep(time_until_start.total_seconds() - 0.1)

        step_sleep = MIN_STEP_DURATION.total_seconds()

        if self.debug > 0:
            print("starting transition")

        for n, i in enumerate(plan["plan"]):
            if self.debug > 0:
                print(str(n) + ", ", end="")
            while datetime.datetime.now() < i["step_start_time"]:
                time.sleep(step_sleep)

            # this translates color_temp to 'kelvin' input
            apply_attrs(transition_type, i[transition_type])
            if self.debug > 1:
                print({transition_type: i[transition_type]})

            time.sleep(step_sleep)

            if self.debug > 0 and n + 1 >= plan["details"]["steps"]:
                print("\n", i)

        if self.debug > 0:
            print("transition completed after", n + 1, "steps")

    def lightswitch(self, power=True):
        """ turns light on if power=true, off if power=false."""

        attrs = {"entity_id": self.entity_id}
        if power:
            data = self.apireq("services/light/turn_on", "post", attrs)
        else:
            data = self.apireq("services/light/turn_off", "post", attrs)

        return data

    def toggle(self):
        """ turns light off if on; on if off. """

        attrs = {"entity_id": self.entity_id}
        data = self.apireq("services/light/toggle", "post", attrs)
        return data
