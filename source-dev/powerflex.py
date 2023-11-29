
import sys, os
import logging
import requests
import pandas as pd
from logging.handlers import RotatingFileHandler
import time as t
from datetime import datetime, date

def _error(msg):
    print(f"ERROR [powerflex]: {msg}",file=sys.stderr)

# these can be changed in ~/.powerflex/powerflex_access.py
logger_name = 'POWERFLEX_LOGS'
DEBUG = False
URLS = {
    "SLAC": {
        "LOGIN": "https://slac.powerflex.com:9443/login",
        "MEASUREMENT": "https://slac.powerflex.com:9443/get_measurement_data",
        "GET_SIGNAL": "https://slac.powerflex.com:9443/get_external_signal/3",
        "SET_SIGNAL": "https://slac.powerflex.com:9443/set_external_signal/3",
        "SET_MAX_POWER_SCHEDULE": "https://slac.powerflex.com:9443/set_max_power_schedule/3",
    },
    "POWERFLEX": {
        "LOGIN": "https://archive.powerflex.com/login",
        "ARCHIVE_01": "https://archive.powerflex.com/get_csh/0032/01",
        "ARCHIVE_02": "https://archive.powerflex.com/get_csh/0032/02"
    }
}
try:
    from powerflex_config import *
except:
    _error("powerflex_config.py not found - using default configuration")

username = 'user@example.org'
password = 'password123'
accountid = '00'
sys.path.append(os.path.join(os.environ["HOME"],".powerflex"))
try:
    from powerflex_access import *
except:
    _error("powerflex_access.py not found in sys.path - using default access credentials")

logger = logging.getLogger(logger_name)

def init_logging():
    """
    Simple logging abstraction. We currently use Rotating File Handler.
    We may, however, in the future, plug in something like Papertrail
    """
    logger.setLevel(logging.DEBUG)
    # set a common log format
    logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    # setup our rotating file handler and assign our common formatter to it
    rotating_file_handler = RotatingFileHandler('my_log.log', maxBytes=200000, backupCount=10)
    rotating_file_handler.setFormatter(logFormatter)
    logger.addHandler(rotating_file_handler)

    # print to stdout if we are debugging
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logFormatter)
    logger.addHandler(stream_handler)

def get_request_base_headers():
    """
    Every single request REQUIRES these headers at a minimum
    Here we provide a simple, testable way to ensure the base headers
    are what they should be
    """
    return {"cache-control": "no-cache", "content-type": "application/json"}

def set_authentication_headers(token):
    """
    Provides a mechanism for the caller to update the base headers with the
    authentication params for a given request. In this particular case, we
    expect a token, which we then set on the base headers as:
    Authorization: Bearer {token}
    """
    headers = get_request_base_headers()
    headers["Authorization"] = f"Bearer {token}"
    return headers

def perform_login(url, username, password):
    """
    Authenticate a user and retrieve the associated bearer token
    """
    headers = get_request_base_headers()
    login_payload = {"username": username, "password": password}
    r = requests.post(url, headers=headers, json=login_payload)
    if r.status_code == requests.codes.ok and "access_token" in r.json():
        return r.json()["access_token"]
    return None

def get_data(url, headers, payload):
    """
    This isn't abstracted out because it should really be a GET and not a POST,
    but the powerflex api doesn't allow it.
    """
    r = requests.post(url, headers=headers, json=payload)
    if r.status_code == requests.codes.ok:
        return r.json()

    logger.info(f"Could not retrieve data from {url}. Status Code: {r.status_code}")
    return None

def get_interval_data(headers, type, time_filter):
    """
        Attempt to retrieve interval data for the given interval. If successfully
        retrieved, save it to s3, otherwise, raise a ValueError
        """
    df = pd.DataFrame()
    interval_payload = {"measurement": type, "time_filter": [time_filter[0], time_filter[1]]}
    data = get_data(URLS["SLAC"]["MEASUREMENT"], headers, interval_payload)

    logger.info("Current Interval Payload")
    logger.info(interval_payload)

    if data is None:
        raise ValueError(f"Could not retrieve interval data; request failed")

    columns = data["data"]["results"][0]["series"][0]["columns"]
    df = pd.concat([df,pd.DataFrame(data=data["data"]["results"][0]["series"][0]["values"], columns=columns)])
    df = df[df['acc_id'] == accountid]
    df.reset_index(drop=True, inplace=True)

    if type == 'ct_response':
        df = df[['time', 'acc_id', 'acs_id', 'charging_state', 'energy_delivered', 'mamps_actual',
                 'pilot_actual', 'power', 'voltage']]

    elif type == 'evse_request':
        df = df[['mamps_limit', 'mamps_rampdown']]

    elif type == 'evse_response':
        df = df[['connected', 'contactor', 'response_period']]
    else:
        logger.info("type not valid: ", type)
        return None

    return df

def process_interval_data(headers, time_filter):
    """
    Attempt to retrieve interval data for the given interval and bundle them together. If successfully
    retrieved, save it to s3, otherwise, raise a ValueError
    """
    df_ct = get_interval_data(headers=headers, type='ct_response', time_filter=time_filter)
    df_request = get_interval_data(headers=headers, type='evse_request', time_filter=time_filter)
    df_response = get_interval_data(headers=headers, type='evse_response', time_filter=time_filter)

    return (df_ct, df_request, df_response)

def get_external_signal(headers):
    data = get_data(URLS["SLAC"]["GET_SIGNAL"], headers=headers, payload={"name":"DCM_EVSE_Allocation"})

    if data is None:
        raise ValueError(f"Could not retrieve external signal; request failed")

    logger.info("Current External Signal")
    logger.info(data)

    return data

def set_max_power_schedule(headers, max_load=13):
    # Max load is an int
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    today = date.today()
    current_day = today.strftime("%d")
    schedule = [{"start_time": current_time, "max_power": max_load}]
    days = [1,2,3,4,5,6,7]
    definition = [{"days":days, "schedule": schedule}]
    payload = {"definition":definition, "max_power_units": "kW", "is_enabled": True, "timezone": "US/Pacific"}
    data = get_data(URLS["SLAC"]["SET_MAX_POWER_SCHEDULE"], headers=headers, payload=payload)
    if data is None:
        raise ValueError(f"Could not set max power schedule; request failed")

    logger.info("Current Set Max Power Schedule")
    logger.info(data)

    return data


def set_external_signal(headers, max_load):
    data = get_data(URLS["SLAC"]["SET_SIGNAL"], headers=headers, payload={"max_load":max_load, "max_load_unit":"kW",
                                                                          "is_enabled": True, "name":"DCM_EVSE_Allocation"})

    if data is None:
        raise ValueError(f"Could not set external signal; request failed")

    logger.info("Current Set External Signal")
    logger.info(data)

    return data

# def main(username, password, get_interval, get_session, debug_mode):
#TODO: Remove everything from session and just leave from interval
def main(username, password, debug_mode, max_load):
    global DEBUG
    DEBUG = debug_mode

    try:
        # Login to SLAC and get the respective tokens
        slac_token = perform_login(URLS["SLAC"]["LOGIN"], username, password)

        # if either api request failed, raise an exception
        if slac_token is None:
            raise ValueError(f"Could not login to SLAC at {URLS['SLAC']['LOGIN']}")

        # get the appropriate auth'ed headers
        slac_auth_headers = set_authentication_headers(slac_token)
        # powerflex_auth_headers = set_authentication_headers(powerflex_token)

        # # get the time interval we want to use for the data request, in seconds
        # interval_datetime = get_date_obj_from_offset(INTERVAL_DAY_OFFSET)
        # session_datetime = get_date_obj_from_offset(SESSION_DAY_OFFSET)
        #
        # am_interval = get_timestamp(interval_datetime, AM_START, AM_END)
        # pm_interval = get_timestamp(interval_datetime, PM_START, PM_END)
        # am_session = get_timestamp(session_datetime, AM_START, AM_END)
        # pm_session = get_timestamp(session_datetime, PM_START, PM_END)
        get_signal = None
        data = None
        set_signal = None

        try:
            logger.info("Retrieving external signal...")
            # set_signal = set_external_signal(slac_auth_headers,max_load=max_load)
            set_signal = set_max_power_schedule(slac_auth_headers, max_load)
        except ValueError as e:
            logger.info(e)
        #TODO If returns empty means it worked
        try:
            logger.info("Retrieving external signal...")
            get_signal = get_external_signal(slac_auth_headers)
        except ValueError as e:
            logger.info(e)

        curr_time = int(t.time())
        # lastly, request, process and save the interval data
        try:
            logger.info("Retrieving interval data...")
            data = process_interval_data(slac_auth_headers, [curr_time-(30), curr_time])
            # return data
        except ValueError as e:
            logger.info(e)

        return (data, get_signal, set_signal)
    except requests.exceptions.ConnectionError as e:
        logger.info("Looks like we can't access the internet right now...😑")

if __name__ == "__main__":
    init_logging()
    # For testing now: max_load as input to curtail. Ideally the default should be 13 and a message published to the topic would update that
    # Need to update main
    retval = main(username=username, password=password, debug_mode=DEBUG, max_load=13)
    data = retval[0]
    if data != None:
        result = pd.concat([data[0], data[1], data[2]], axis=1, join='inner')
        result["timestamp"] = [datetime.fromtimestamp(x) for x in result["time"]]
        pd.options.display.max_rows = None
        pd.options.display.max_colwidth = None
        pd.options.display.max_columns = None
        pd.options.display.width = None
        print(result.set_index("timestamp"))

