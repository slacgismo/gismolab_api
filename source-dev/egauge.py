"""
2 - Implement egauge data pull with local rest api. Endpoints are:
egauge house B: http://198.129.116.113/cgi-bin/egauge?ins&tot
egauge house A: http://198.129.119.226/cgi-bin/egauge?ins&tot 
"""

# egauge house B ip: 198.129.116.113
# egauge house A ip: 198.129.119.226

import sys, os
import datetime
from xml.etree import ElementTree as ET
import requests
from requests.auth import HTTPDigestAuth
import time
import json
import xmltodict
import AWSIoTPythonSDK.MQTTLib as AWSIoTPyMQTT

def _error(msg):
    print(f"ERROR [egauge]: {msg}",file=sys.stderr)

mode = 'web'
endpoint = 'egauge47571.egaug.es/'
wait_time = 0.1
try:
    from egauge_config import *
except:
    _error("egauge_config.py not found - using default configuration")

user = 'username'
password = 'password'
sys.path.append(os.path.join(os.environ["HOME"],".egauge"))
try:
    from egauge_access import *
except:
    _error("egauge_access.py not found in sys.path - using default access credentials")


class EgaugeInterface():

    def __init__(self, mode=mode, endpoint=endpoint, username=user, password=password, t_sample=wait_time, topic=None, clientid=None):
        # Initializing credentials
        self.endpoint = endpoint
        self.mode = mode
        self.username = username
        self.password = password
        self.TOPIC_PUBLISH_EGAUGE = topic
        self.CLIENT_ID = clientid

        # Initializing parameters
        self.t_sample = t_sample
        self.keys = ["A.Battery", "A.SubPanel", "A.GridPower", "A.Solar", "A.EV", "ts"]

    # Function to process data from e-gauge and convert to useful power values
    def processing_egauge_data(self):
        if self.endpoint == None:
            _error('endpoint is None')
            return 'Error egauge: endpoint is none'
        self.url = 'http://' + self.endpoint + '/cgi-bin/egauge?ins&tot'
        power_values = dict.fromkeys(self.keys, None)
        try:
            if self.mode == 'web':
                resp = requests.get(self.url, auth=HTTPDigestAuth(self.username, self.password))
            elif self.mode == 'ip':
                resp = requests.get(self.url)
            else:
                print('mode type not acceptable')
                return 'Error egauge: mode type not acceptable'

            resp.raise_for_status()
            data_ini = self.get_egauge_registers(resp)

        except requests.exceptions.HTTPError as err:
            _error(err)
            return {"error":str(err)}

        time.sleep(self.t_sample)

        try:
            if self.mode == 'web':
                resp = requests.get(self.url, auth=HTTPDigestAuth(self.username, self.password))
                resp.raise_for_status()
            elif self.mode == 'ip':
                resp = requests.get(self.url)
                resp.raise_for_status()
            else:
                print('mode type not acceptable')
                return 'Error egauge: mode type not acceptable'

            data_end = self.get_egauge_registers(resp)

        except requests.exceptions.HTTPError as err:
            _error(err)
            return {"error":str(err)}

        ts_delta = data_end['ts'] - data_ini['ts']
        try:
            for i in power_values:
                if i == 'ts':
                    power_values['ts'] = datetime.datetime.fromtimestamp(int(data_end['ts'])).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    power_values[i] = round(((data_end[i] - data_ini[i]) / ts_delta) / 1000, 3)

        except Exception as e:
            _error('Error retrieving data from E-Gauge API: ', e)
            return {"error":str(err)}

        return power_values

    def get_egauge_registers(self, response):
        power_values = dict.fromkeys(self.keys, None)
        data = xmltodict.parse(response.text)
        data_json = json.loads(json.dumps(data))
        keys_set = self.keys
        if data_json['data']['ts'] != None:
            power_values['ts'] = int(data_json['data']['ts'])
        egauge_vals = data_json['data']['r']

        for i in egauge_vals:
            if i['@n'] in keys_set:
                power_values[i['@n']] = int(i['v'])

        return power_values


if __name__ == "__main__":
    # Results are in kW
    retval = EgaugeInterface(mode=mode, endpoint=endpoint, username=user, password=password).processing_egauge_data()
    print(retval)

