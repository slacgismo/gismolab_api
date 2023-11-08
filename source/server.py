"""GISMoLab API
"""
import os, sys

#
# Default configuration
#
port = 5000 # Incoming request port
host = "127.0.0.1" # Incoming connections address mask (use "0.0.0.0" to allow all incoming addresses)
ssl_context = None # use 'adhoc' for self-signed HTTPS
cache_expire = 60 # Cache age limit
enable_cors = True # False disables CORS checking
autoupgrade = False # True to enable automatic module upgrades

try:
    from server_config import *
except:
    device_types = []

# dev venv maintenance
if auto_upgrade and __name__ == "__main__" and os.path.exists("../requirements.txt"):
    print("Updating python environment to latest module versions...",file=sys.stderr,flush=True)
    assert(not os.system("python3 -m pip install pip --upgrade -r ../requirements.txt 1>/dev/null"))

import json
import random
import datetime as dt
import time
import copy
import threading

from flask import Flask, jsonify, request, Response

from data import Data, fields
import collector as co
from device import *

#
# Keys and token
#
def _get_guid():
    return hex(random.randint(0,1e64-1))[2:]

facility_data = {}

def _load_facility_data():
    global facility_data
    try:
        from facility_data import facility_data
    except:
        if not facility_data:
            user = os.environ["USER"] if "USER" in os.environ else "user"
            domain = os.environ["HOSTNAME"] if "HOSTNAME" in os.environ else "domain"
            facility_data[_get_guid()] = dict(
                name = "New facility",
                contact = f"{user}@{domain}",
                )
        _save_facility_data()
    print("FACILITIES DATA",file=sys.stderr)
    print(f"  {'Name':20s} {'Contact':20s} {'Key':64s}",file=sys.stderr)
    print(f"  {'-'*20} {'-'*20} {'-'*64}",file=sys.stderr)
    for key,facility in facility_data.items():
        print(f"  {facility['name']:20s} {facility['contact']:20s} {key})",file=sys.stderr)

def _save_facility_data():
    with open("facility_data.py","w") as fh:
        print(f"facility_data = {facility_data}",file=fh)

_load_facility_data()

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


#
# Device access
#

device_data = {
    # "test" : {"lock":None,"data":None,"token":None},
}

@_app.route("/device/<device_id>/add",methods=["GET","PUT","POST"])
def api_device_add(device_id):
    """TODO"""
    key = _get_arg("key")
    if not key in facility_data:
        return _failed(E_UNAUTHORIZED,"access denied")
    token = _get_guid()
    device_data[device_id] = {"lock":None,"data":None,"token":token}
    print(f"New device token for {facility_data[key]['name']}: {token}",file=sys.stderr)
    return _success(token=token)

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
    elif token != facility_data:
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

swag = swagger(_app)
swag['info']['version'] = "1.0"
swag['info']['title'] = "GISMoLab API"
swag['servers'] = {"url":f"https://{host}:{port}/"}
with open(f"{_app.name}-swagger.json","w") as fh:
    json.dump(swag,fh,indent=4)

@_app.route("/",methods=["GET"])
def root():
    """Get API Specification
    ---
    responses:
        200:
            description: API specifications
            content: application/json
    """
    return _success(swag)

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
