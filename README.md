# GISMo Lab (SLAC Building 27) APIs

**WARNING: THIS REPOSITORY MUST REMAIN STRICTLY PRIVATE**

# System Architecture

![System Architecture](/docs/system_architecture.png)

The server is designed to run either inside or outside the network hosting the
devices. When running outside the network, the server must receiving incoming
device status updates and requests.

# General Commands

## Device Control

### Device Enrollment

Devices in the GISMo Lab must register with the internal server to permit user
access.  This is done using the
`GET /device/<device_id>/start?token=device_key` API endpoint, where
`device_id` is the device identifier, and `device_key` is the current device
key.  A single device key is used for all devices in a facility, which is
stored in `device_keys.py`.

    GET /device/<device-id>/add?key=<device-key>

This request generates a device token to allow devices to access incoming and deliver
outgoing traffic from the facility.



## 


# Server Start

Run the following:

~~~
cd source
python3 -m server
~~~

## Check status

Run the following command:

~~~
curl http://localhost:5001/
~~~

## Monitor

Setup the monitor in Marimo

~~~
cd source
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install pip --upgrade -r ../requirements.txt
~~~

Start the server

~~~
python3 server.py > server.log &
~~~

Run the monitor

~~~
marimo run monitor.py
~~~

## Online API docs

Run the following command:

~~~
curl http://localhost:5001/docs
~~~

## Swagger API

TODO

