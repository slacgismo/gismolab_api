# GISMo Lab (SLAC Building 27) APIs

**WARNING: THIS REPOSITORY MUST REMAIN STRICTLY PRIVATE**

# System Architecture

![System Architecture](/docs/system_architecture.png)

## Powerflex Setup

Create the file `~/.powerflex/powerflex_access.py` and add the following:

~~~
username = 'user@example.org'
password = 'password123'
~~~

## Sonnen Setup

Create the file` ~/.sonnen/sonnen_access.py` and add the following:

~~~
token='0123456789abcdef'
serial='01234'
~~~

## Server Start

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

