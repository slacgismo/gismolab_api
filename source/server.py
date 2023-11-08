"""GISMoLab API
"""
import os, sys

# dev venv maintenance
if __name__ == "__main__" and os.path.exists("../requirements.txt"):
    RC_OK = 0
    print("Updating python environment to latest module versions...",file=sys.stderr,flush=True)
    assert(os.system("python3 -m pip install pip --upgrade -r ../requirements.txt 1>/dev/null")==RC_OK)

import json
import random
import datetime as dt
import time
import copy
import threading

from flask import Flask, jsonify, request, Response

import powerflex as pf
import sonnen as sb
import egauge as eg
import shelly as sp
from data import Data, fields
import collector as co
from device import *

#
# Default configuration
#
port = 5000 # Incoming request port
host = "127.0.0.1" # Incoming connections address mask (use "0.0.0.0" to allow all incoming addresses)
ssl_context = None # use 'adhoc' for self-signed HTTPS
cache_expire = 60 # Cache age limit
enable_cors = True # False disables CORS checking

try:
    from server_config import *
except:
    device_ipaddr = scan_network()

try:
    from device_key import device_key
except:
    device_key = None
if not device_key:
    device_key = hex(random.randint(0,1e64-1))[2:]
    with open("device_key.py","w") as fh:
        print(f"device_key = '{device_key}'",file=fh)
    print(f"device_key = {device_key}",file=sys.stderr)

#
# Argument processing
#

def _get_arg(name,astype=str):
    value = request.args.get(name)
    return None if value is None else astype(value)

#
# Caching
#
cache = {}

def get_cache(key):
    age_cache()
    return cache[key]["data"]

def set_cache(key,data):
    cache[key] = {
        "time" : time.time(),
        "data" : data,
    }

def age_cache():
    expired = time.time() - cache_expire
    for key in list(cache.keys()):
        if cache[key]["time"] < expired:
            del cache[key]

#
# Result handling
#

E_OK = 200
def _success(**kwargs):
    return jsonify(dict(
        status = "OK",
        data = kwargs,
        )),E_OK

E_BADREQUEST = 400
E_UNAUTHORIZED = 401
E_FORBIDDEN = 403
E_NOTFOUND = 404
E_NOTALLOWED = 405
E_TIMEOUT = 408
E_CONFLICT = 409
E_GONE = 410

def _failed(code,message,**kwargs):
    if not message:
        message = f"HTTP code {code}"
    result = dict(
        status = "ERROR",
        code = code,
        message = message,
        )
    if kwargs:
        result["data"] = kwargs
    return result,code

def _error(msg,**kwargs):
    return jsonify({"error":str(msg),"data":kwargs})

#
# Status
#
status = {
    "powerflex" : {},
    "sonnen" : {},
    "egauge" : {},
    "shelly" : {},
}
devices = {
    "plug" : {},
    "evcharger" : {},
    "meter" : {},
    "battery" : {},
    "hvac" : {},
    "waterheater" : {},
}
for key in status:
    status[key] = {
        "status" : "UNKNOWN", 
        "last_update" : None,
    }
    
#
# Powerflex interface
#

try:
    pf_token = pf.perform_login(pf.URLS["SLAC"]["LOGIN"], pf.username, pf.password)
    pf_auth_headers = pf.set_authentication_headers(pf_token)
except Exception as err:
    pf_token = None
    pf_auth_headers = None
    print(f"ERROR [server]: {err}",file=sys.stderr)

def _powerflex_update(curr_time=None,duration=None):

    if not curr_time:
        curr_time = int(time.time())
    
    if not duration:
        duration = 60
    
    key = f"powerflex/{curr_time}/{duration}"
    try:
        result = get_cache(key)
    except KeyError:
        try:

            data = pf.process_interval_data(pf_auth_headers, [curr_time-duration, curr_time])[0]
            status["powerflex"]["status"] = "OK"
            status["powerflex"]["last_update"] = int(time.time())
        
        except Exception as err:
        
            status["powerflex"]["status"] = "ERROR"
            return _error(err,context="powerflex")

        data["time"] = [dt.datetime.fromtimestamp(int(x)).strftime("%Y-%m-%d %H:%M:%S %Z") for x in data["time"]]
        result = data.set_index(["acc_id","acs_id","time"]).sort_index()
        set_cache(key,result)

    return result

#
# Sonnen Interface
#
sb = sb.SonnenInterface()

def _sonnen_update():
    curr_time = int(time.time())
    key = f"/sonnen"
    try:
        result = get_cache(key)
    except KeyError:
        try:
            result = sb.get_status()
            status["sonnen"]["status"] = "OK"
            status["sonnen"]["last_update"] = int(time.time())
        except:
            status["sonnen"]["status"] = "ERROR"
            return _error(err,context="sonnen")
        set_cache(key,result)
    
    return result

#
# Egauge Interface
#
eg = eg.EgaugeInterface()

def _egauge_update():
    curr_time = int(time.time())
    key = f"/egauge"
    try:
        result = get_cache(key)
    except KeyError:
        try:
            result = eg.processing_egauge_data()
            status["egauge"]["status"] = "OK"
            status["egauge"]["last_update"] = int(time.time())
        except:
            status["egauge"]["status"] = "ERROR"
            return _error(err,context="egauge")
        set_cache(key,result)
    
    return result    

#
# Shelly Interface
#

def _shelly_update():
    try:
        data = sp.get_data()
    except Exception as err:
        data = dict(error=str(err))
    if "error" in data:
        return dict(status="ERROR",message=data["error"])
    else:
        result = {}
        for name,values in data.items():
            result[name] = Data(status="OK",
                last_update = time.time(),
                energy = values['status']['aenergy']['total'],
                power = values['status']['apower'],
                current = values['status']['current'],
                voltage = values['status']['voltage'],
                current_control = values['config']['current_limit'] if values['status']['output'] else 0.0,
                voltage_control = values['config']['voltage_limit'] if values['status']['output'] else 0.0,
                power_control = values['config']['power_limit'] if values['status']['output'] else 0.0,
                device_state = "ON" if values['status']['output'] else "OFF",
                )
        return result

#
# API Endpoints
#
_app = Flask("gismolab")

@_app.after_request
def _after_request(response: Response) -> Response:
    if not enable_cors:
        response.headers['Access-Control-Allow-Methods'] = '*'
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Vary']='Origin'
    return response


# @_app.route("/")
# def api_root():
#     """Get interfaces and device list
#     ---
#     responses:
#         200:
#             description: List of available interfaces and devices
#             content: application/json
#     """
#     return _success(interfaces=status,devices=devices)

# @_app.route("/stop")
# def api_stop():
#     """Emergency stop
#     ---
#     responses:
#         200:
#             description: TODO
#             content: application/json
#     """
#     try:
#         Device.all_stop()
#         return _success()
#     except Exception as err:
#         return _error(err,)

# @_app.route("/powerflex")
# def api_powerflex():
#     """Get powerflex status
#     ---
#     responses:
#         200:
#             description: TODO
#             content: application/json
#     """
#     return jsonify(status["powerflex"])

# @_app.route("/powerflex/json/<orient>")
# def api_powerflex_json(orient):
#     """Get powerflex historical data
#     See pandas.DataFrame.to_json() for valid values of <orient>
#     ---
#     responses:
#         200:
#             description: TODO
#             content: application/json
#     """
#     try:
#         curr_time = int(request.args.get("time"))
#         assert(curr_time>0)
#     except:
#         curr_time = None

#     try:
#         duration = int(request.args.get("duration"))
#         assert(duration>0)
#     except:
#         duration = None

#     try:

#         return _powerflex_update(curr_time,duration).to_json(orient=orient)

#     except Exception as err:

#         return _error(err,context="powerflex")

# @_app.route("/powerflex/csv")
# def api_powerflex_csv():
#     """Get powerflex historical data
#     See pandas.DataFrame.to_csv() for details
#     ---
#     responses:
#         200:
#             description: TODO
#             content: application/json
#     """
#     try:
#         curr_time = int(request.args.get("time"))
#         assert(curr_time>0)
#     except:
#         curr_time = None

#     try:
#         duration = int(request.args.get("duration"))
#         assert(duration>0)
#     except:
#         duration = None

#     try:

#         return _powerflex_update(curr_time,duration).to_csv(index=True,header=True)

#     except Exception as err:

#         return _error(err,context="powerflex")

# @_app.route("/evchargers",methods=["GET"])
# def api_evchargers():
#     """Get EV charger device list
#     Returns a list of available EV charger devices.
#     ---
#     responses:
#         '200':
#             description: list of EV charger names
#             content:
#                 application/json:
#                     schema:
#                         type: array
#                         items:
#                             type: string
#         default:
#             description: Unexpected error
#     """
#     return jsonify([])

# @_app.route("/sonnen")
# def api_sonnen():
#     """Get Sonnen battery device list
#     ---
#     responses:
#         200:
#             description: TODO
#             content: application/json
#     """
#     return jsonify(_sonnen_update())

# @_app.route("/batterys")
# def api_batterys(): # apologys to the English language police but API conventions demand this plural form
#     """Get batteries device list
#     ---
#     responses:
#         200:
#             description: TODO
#             content: application/json
#     """
#     return jsonify([])
    
# @_app.route("/egauge")
# def api_egauge():
#     """Get Egauge metering status
#     ---
#     responses:
#         200:
#             description: TODO
#             content: application/json
#     """
#     return jsonify(_egauge_update())

# @_app.route("/meters")
# def api_meters():
#     """Get meter device list
#     ---
#     responses:
#         200:
#             description: TODO
#             content: application/json
#     """
#     return jsonify([])
    
# @_app.route("/shelly")
# def api_shelly():
#     """Get Shelly switch device list
#     ---
#     responses:
#         200:
#             description: TODO
#             content: application/json
#     """
#     return jsonify(sp.get_data())

# @_app.route("/shelly/scan")
# def api_shelly_scan():
#     """Get Shelly switch status
#     ---
#     responses:
#         200:
#             description: TODO
#             content: application/json
#     """
#     try:
#         network = request.args.get("network").split(',')
#     except:
#         network = None
#     try:
#         sp.verbose_enable = True
#         if not devices["plug"]:
#             devices["plug"] = sp.scan_network(network)
#         return jsonify(devices["plug"])
#     except Exception as err:
#         return _error(err)

# @_app.route("/plugs")
# def api_plugs():
#     """Get plug device list
#     ---
#     responses:
#         200:
#             description: TODO
#             content: application/json
#     """
#     result = sp.get_data()
#     if "error" in result:
#         return jsonify(result)
#     else:
#         devices["plug"] = list(result.keys())
#     return jsonify(devices["plug"])

# @_app.route("/plug/<name>")
# def api_plug_name(name):
#     """Get plug device
#     ---
#     responses:
#         200:
#             description: TODO
#             content: application/json
#     """
#     data = _shelly_update()[name]
#     fmt = request.args.get("format")
#     valid = [x for x in dir(data) if x.startswith("as_") and callable(getattr(data,x))]
#     if not fmt:
#         fmt = "json"
#     elif not f"as_{fmt}" in valid:
#         return _error(f"'format={fmt}' is not valid")
#     if fmt == "html":
#         return str(data.as_html(caption=name.replace('_',' ').title()+"<hr/>")) + '\n'
#     else:
#         return str(getattr(data,f"as_{fmt}")()) + '\n'

# @_app.route("/plug/<name>/on")
# def api_plug_name_on(name):
#     """Turn plug device on
#     ---
#     responses:
#         200:
#             description: TODO
#             content: application/json
#     """    
#     old = sp.set_switch(name,True)
#     return jsonify(old)

# @_app.route("/plug/<name>/off")
# def api_plug_name_off(name):
#     """Turn plug device off
#     ---
#     responses:
#         200:
#             description: TODO
#             content: application/json
#     """
#     old = sp.set_switch(name,False)
#     return jsonify(old)

# @_app.route("/hvacs")
# def api_hvacs():
#     """Get list of HVAC devices
#     ---
#     responses:
#         200:
#             description: TODO
#             content: application/json
#     """
#     return jsonify([])
    
# @_app.route("/waterheaters",methods=["GET"])
# def api_waterheaters():
#     """Get list of waterheater devices
#     ---
#     responses:
#         200:
#             description: Waterheater list
#             content: application/json
#             schema:
#                 type: list
#     """
#     return jsonify([])    

#
# Device control
#

device_data = {
    "test" : {"lock":None,"data":None,"token":None},
}

@_app.route("/device/<device_id>/add",methods=["GET","PUT","POST"])
def api_device_add(device_id):
    """TODO"""
    key = _get_art("key")
    if token != device_key:
        return _failed(E_UNAUTHORIZED,"access denied")
    device_data[device_id] = {"lock":None,"data":None,"token":None}
    return _failed(E_BADREQUEST)

@_app.route("/device/<device_id>/start",methods=["GET"])
def api_start_deviceid(device_id):
    """Start device command handling
    ---
    parameters:
      - in: path
        name: device_id
        schema:
          type: string
        required: true
        description: Device identifier
    responses:
      200:
        description: Confirmation, token can be used for send/get operations
        content: application/json
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                token:
                  type: string
                  description: User access token
              description: Data payload
            status:
              type: string
              description: Response status
      404:
        description: Device not found, device_id is not listed in available device
        content: application/json
        schema:
          type: object
          properties:
            message:
              type: string
              description: Error message
            status:
              type: string
              description: Response status
            code:
              type: integer
              description: HTTP error code
      405:
        description: Device is busy, device_id is already being controlled by another user
        content: application/json
        schema:
          type: object
          properties:
            message:
              type: string
              description: Error message
            status:
              type: string
              description: Response status
            code:
              type: integer
              description: HTTP error code
    """

    # device must be listed in available device data dictionary
    if not device_id in device_data:

        return _failed(E_NOTFOUND,"device not found")

    # device already has a data lock enabled
    elif device_data[device_id]["lock"]:

        return _failed(E_NOTALLOWED,"device busy")

    # device is available 
    else:

        # create the data lock
        device_data[device_id]["lock"] = threading.Event()

        # create an access token
        token = hex(random.randint(0,1e64-1))[2:]
        device_data[device_id]["token"] = token
        return _success(token=token)

@_app.route("/device/<device_id>/stop",methods=["GET"])
def api_stop_deviceid(device_id):
    """Stop device command handling
    ---
    parameters:
      - in: path
        name: device_id
        schema:
          type: string
        required: true
        description: Device identifier
      - in: query
        name: token
        schema:
          type: string
        required: true
        description: Access token
    responses:
      200:
        description: Confirmation
        content: application/json
        schema:
          type: dict
      401:
        description: Not authorized
      408:
        description: Device not found
        content: application/json
        schema:
          type: dict
      410:
        description: Device not waiting
        content: application/json
        schema:
          type: dict
    """
    token = _get_arg("token")
    if not device_id in device_data:
        return _failed(E_NOTFOUND,"device not found")
    elif not device_data[device_id]["lock"]:
        return _failed(E_GONE,"device not active")
    elif device_data[device_id]["token"] != token:
        return _failed(E_UNAUTHORIZED,"access denied")
    else:
        device_data[device_id]["lock"] = None
        device_data[device_id]["token"] = None
        return _success()    

@_app.route("/device/<device_id>/recv",methods=["GET"]) 
def api_recv_deviceid(device_id):
    """Receive device command
    ---
    parameters:
      - in: path
        name: device_id
        schema:
          type: string
        required: true
        description: Device identifier
      - in: query
        name: token
        schema:
          type: string
        required: true
        description: Access token
      - in: query
        name: timeout
        schema:
          type: int
        description: Receive timeout in seconds
    responses:
      200:
        description: Device command
        content: application/json
        schema:
          type: dict
      400:
        description: Bad request
        content: application/json
        schema:
          type: dict
      401:
        description: Not authorized
        content: application/json
        schema:
          type: dict
      404:
        description: Device not found
        content: application/json
        schema:
          type: dict
      408:
        description: Receive timeout
        content: application/json
        schema:
          type: dict                
    """
    token = _get_arg("token")
    try:
        timeout = _get_arg("timeout",int)
    except Exception as err:
        return _failed(E_BADREQUEST,str(err))
    if not device_id in device_data:
        return _failed(E_NOTFOUND,"device not found")
    elif token != device_key:
        return _failed(E_NOTALLOWED,"access denied")
    else:
        command = device_data[device_id]
        if not command["lock"]:
            return _failed(E_NOTALLOWED,"device not accepting data")
        if command["lock"].wait(timeout):
            device_data[device_id]["lock"]
            response = command["data"]
            command["lock"].clear()
            command["data"] = None
            return _success(**response)
        else:
            return _failed(E_TIMEOUT,"device receive timeout")

@_app.route("/device/<device_id>/send",methods=["GET","PUT","POST"])
def api_send_deviceid(device_id):
    """Send device command
    ---
    parameters:
      - in: path
        name: device_id
        schema:
          type: string
        required: true
        description: Device identifier
      - in: query
        name: token
        schema:
          type: string
        required: true
        description: Access token
      - in: query
        name: variable_name
        required: true
        schema:
          type: dict
        description: Data to deliver to device
    responses:
      200:
        description: Device command
        content: application/json
    """
    token = _get_arg("token")
    if not device_id in device_data:
        return _failed(E_NOTFOUND,"device not found")
    elif device_data[device_id]["token"] != token:
        return _failed(E_UNAUTHORIZED,"access denied")
    else:
        command = device_data[device_id]
        if not command["lock"]:
            return _failed(E_NOTALLOWED,"device not accepting data")
        data = {"timestamp":time.time()}
        for field in fields:
            value = request.args.get(field)
            if value:
                data[field] = request.args.get(field)
        command["data"] = data
        command["lock"].set()
        return _success()

@_app.route("/device/<device_id>/get",methods=["GET"])
def api_get_deviceid(device_id):
    """Get device data
    ---
    parameters:
      - in: path
        name: device_id
        schema:
          type: string
          required: true
          description: Device identifier
      - in: query
        name: token
        schema:
          type: string
        required: true
        description: Access token
    responses:
      200:
        description: Device data
        content: application/json
        schema:
          type: object
        required: true
    """     
    return _failed(E_BADREQUEST,"not supported")

#
# Swagger API Spec
#

from flask_swagger import swagger

@_app.route("/spec",methods=["GET"])
def spec():
    """Get API Specification
    ---
    responses:
        200:
            description: API specifications
            content: application/json
    """
    return _success(swag)

swag = swagger(_app)
swag['info']['version'] = "1.0"
swag['info']['title'] = "GISMoLab API"
swag['servers'] = {"url":f"https://{host}:{port}/"}
with open(f"{_app.name}-swagger.json","w") as fh:
    json.dump(swag,fh,indent=4)

#
# Inplace startup
#
if __name__ == "__main__":

    if not enable_cors:
        print("WARNING [server]: CORS is disabled",file=sys.stderr)
    
    if ssl_context is None:
        print("WARNING [server]: SSL disabled",file=sys.stderr)
    elif ssl_context == 'adhoc':
        print("WARNING [server]: using self-signed certificates",file=sys.stderr)

    _app.run(host=host,port=port,ssl_context=ssl_context)
