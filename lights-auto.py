import requests
import json
import datetime
import pickle
import win32api
import fasteners
from pathlib import Path


# Triggers an automation which sets light brightness/color temp in the office based on certain criteria:
# Time of day, whether or not I'm at home (based on wifi connected network), and keyboard/mouse activity.
# Windows only. Intended to be run on main desktop.

# Make sure PROCESS_DIR is created before running this.

# TODO:
# write tests/debugging output


# HomeAssistant base API URL.
API_URL = "http://1.2.3.4:8123/api/"

# Hours between which this will trigger an update.
# Recommended 7am to 5pm, or 7 & 17, respectively.
START_TIME = 7
END_TIME = 17

# Name of the automation entity to trigger. 
ENTITY_NAME = "automation.daytime_office"

# Home wifi network names. If we're not connected to one of these, skip update. 
HOME_SSIDS = ['wifi1', 'wifi2']

# where we store the log of automation trigger timestamps.
PROCESS_DIR = Path("C:/Users/me/AppData/Local/homeassistant/")
PICKLE_LOCATION = PROCESS_DIR / "lights-auto_log.p"
LOCKFILE = PROCESS_DIR / "lights-auto.lock"



def getIdleTime():
    # Returns the number of seconds since last mouse move/click or keyboard input.
    return (win32api.GetTickCount() - win32api.GetLastInputInfo()) / 1000.0


def check_for_activity(seconds=300):
    if getIdleTime() < seconds:
        return True
    else:
        return False


def trigger_automation():
    # Trigger the homeassistant automation via the api.
    # This works even if the automation is disabled in the UI.
    # When fired this way, it will trigger regardless of any conditions defined in the automation.
    
    payload = {"entity_id": ENTITY_NAME}
    response = requests.post(API_URL + 'services/automation/trigger', json.dumps(payload))
    
    if response.status_code != 200:
        print(response.text)
        print("Error: got unexpected response from HomeAssistant. response status / response text:", 
               response.status_code, response.text)
    else:
        set_trigger_time()


def check_time():
    # See if current time is between START_TIME and END_TIME.
    # Returns True if so. 
    
    cur_hour = datetime.datetime.now().hour
    
    if cur_hour >= START_TIME and cur_hour < END_TIME:
        # skip. only trigger between 7am and 5pm. 
        return True
    else:
        return False


def get_last_trigger():
    # returns last trigger datetime from pickle, or None if unset / error.
    
    try:
        with open(PICKLE_LOCATION,"rb") as f:
            log = pickle.load(f)
            return log[-1]
    except:
        print("error loading pickle file:", PICKLE_LOCATION)
        return None


def set_trigger_time():
    # Pickle is just a list of datetimes, sorted oldest to newest.
    
    # getting/writing separately might be prone to race conditions but... eh
    try:
        with open(PICKLE_LOCATION,"rb") as f:
            log = pickle.load(f)
            
            if len(log) >= 105:
                log = log[-99:]
        
    except:
        #print("xp")
        log = []

    with open(PICKLE_LOCATION,"wb") as f:
        # Retain last 100 timestamps. 

        now = datetime.datetime.now()
        #print("appending:", now)
        log.append(now)
        
        #print(log)
        
        pickle.dump(log, f)


def check_location_by_wifi():
    # Windows only. Returns True if at home; False elsewhere.

    import subprocess
    results = subprocess.check_output(["netsh", "wlan", "show", "interfaces"])
    results = results.decode("ascii").split("\r\n")
    
    # usually just returns one but support multiple just in case
    connected_networks = [i.split(":")[1].strip() for i in results if i.strip().startswith('SSID')]
    
    #print("cn", connected_networks)

    for i in connected_networks:
        if i in HOME_SSIDS:
            #print("home")
            return True

    return False


def main_loop():
    # Main loop.  
    while True:
        time_within_active_hours = check_time()
        if not time_within_active_hours:
            time.sleep(30)
        else:

            at_home = check_location_by_wifi()
            if not at_home:
                #print("away")

                # sleep 20 min before checking again
                time.sleep(1200)
                continue

            else:
                # Second loop here so we only check wifi every 20 minutes.
                
                # trigger only if there's activity on the computer 
                is_active = check_for_activity()
                
                if not is_active:
                    time.sleep(15)
                    continue
                else:

                    # Should probably have this set a local trigger time and check against that before pulling from the pickle.
                    last_trigger_time = None

                    start_ts = datetime.datetime.now()
                    while True:

                        cur_ts = datetime.datetime.now()

                        if not last_trigger_time:
                            last_trigger_time = get_last_trigger()

                        if not last_trigger_time:
                            trigger_automation()
                            time.sleep(6900) #1hr 55 min
                            break
                        else:

                            if cur_ts - last_trigger_time > datetime.timedelta(hour=2):
                                trigger_automation()
                                last_trigger_time = datetime.datetime.now()
                                time.sleep(6900) #1hr 55 min
                                break
                            else:
                                time.sleep(150)

                        if cur_ts - start_ts > datetime.timedelta(minute=20):
                            # go back to outer loop
                            break

            time.sleep(1)

        time.sleep(1)



### main:

a_lock = fasteners.InterProcessLock(LOCKFILE)
gotten = a_lock.acquire(blocking=False, delay=0.1, max_delay=3, timeout=30)
try:
    if gotten:
        main_loop()
    else:
        exit();
        
finally:
    if gotten:
        # not really necessary because the lock releases on process exit
        a_lock.release()