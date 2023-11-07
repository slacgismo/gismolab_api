import marimo

__generated_with = "0.1.41"
app = marimo.App(width="full")


@app.cell
def __():
    #
    # App configuration
    #
    datetime_format = "at %H:%M:%S on %m/%d/%y"
    initial_refresh = 10
    config_update_freq = 10
    # DEBUG = True
    # co.DEBUG = False
    return config_update_freq, datetime_format, initial_refresh


@app.cell
def __(initial_refresh, mo):
    #
    # UI refresh control
    #
    refresh = mo.ui.refresh([1,2,5,10],initial_refresh)
    mo.hstack([mo.md("Screen update rate:"),refresh],justify="end")
    return refresh,


@app.cell
def __(
    change_select,
    data,
    device_config,
    device_names,
    enable,
    err,
    mo,
    refresh,
    scan_devices,
    time,
    ui,
):
    #
    # Main UI
    #
    refresh
    try:
        _time = data["time"]
        apower = data["apower"]
        aenergy = data["aenergy"]["total"]
        voltage = data["voltage"]
        current = data["current"]
        output = data["output"]
        name = device_config["name"]
        _status = f"Status: Device {'on' if output else 'off'}"
    except Exception as err:
        _time = time.time()
        name = ""
        apower = 0.0
        aenergy = 0.0
        output = False
        _status = f"Status: Error -- {err}"
    _power = ui.GoIndicator(
        mode="gauge+number",
        value=round(apower / 1000, 1),
        domain={"x": [0, 1], "y": [0, 1]},
        gauge={"axis": {"range": [0, 2.0]}},
        title={"text": f"{name} Power (kW)"},
    )
    _energy = ui.GoIndicator(
        mode="gauge+number",
        value=round(aenergy / 1000, 1),
        domain={"x": [0, 1], "y": [0, 1]},
        gauge={"axis": {"range": [0, 100]}},
        title={"text": f"{name} Energy (kWh)"},
    )
    _voltage = ui.GoIndicator(
        mode="gauge+number",
        value=round(voltage, 1),
        domain={"x": [0, 1], "y": [0, 1]},
        gauge={"axis": {"range": [0, 280]}},
        title={"text": f"{name} Voltage (V)"},
    )
    _current = ui.GoIndicator(
        mode="gauge+number",
        value=round(current, 1),
        domain={"x": [0, 1], "y": [0, 1]},
        gauge={"axis": {"range": [0, 50]}},
        title={"text": f"{name} Current (A)"},    
    )
    _age = time.time() - _time
    _age = f"Data age: {_age:.3f} seconds"
    tabs = mo.tabs(
        {
            "Power": _power.get_figure(),
            "Voltage": _voltage.get_figure(),
            "Current" : _current.get_figure(),
            "Energy": _energy.get_figure(),
        }
    )
    select = mo.ui.dropdown(
        options=device_names, value=device_config["name"], on_change=change_select
    )
    switch = mo.ui.switch(value=output, on_change=enable)
    rescan = mo.ui.button(label="Refresh", on_click=scan_devices)

    mo.vstack(
        [
            mo.hstack([mo.md("Device:"), select, rescan], justify="start"),
            # mo.hstack([_power.get_figure(),_energy.get_figure()]),
            tabs,
            mo.hstack(
                [
                    mo.hstack([mo.md("Device enable:"), switch], justify="start"),
                    mo.md(_age),
                ]
            ),
            mo.md(_status),
        ]
    )
    return (
        aenergy,
        apower,
        current,
        name,
        output,
        rescan,
        select,
        switch,
        tabs,
        voltage,
    )


@app.cell
def __(json, mo, requests, shelly_config):
    #
    # Device list
    #
    _first = shelly_config.device_ipaddr[0]
    get_select,set_select = mo.state(_first)

    def get_config(ip):
        try:
            config = requests.get(f"http://{ip}/rpc/Switch.GetConfig?id=0")
            if config.status_code == 200:
                return json.loads(config.text.encode())
        except:
            pass
        return dict(name=f"<ipaddr:{ip}>")

    def set_config(ip):
        global device_config
        device_config = get_config(ip)

    def change_select(ip):
        set_select(ip)
        set_config(ip)

    change_select(_first)
    devices_names = {}
    def scan_devices(_=None):
        global device_names
        device_names = dict((get_config(x)['name'],x) for x in shelly_config.device_ipaddr)
    scan_devices()
    return (
        change_select,
        device_config,
        device_names,
        devices_names,
        get_config,
        get_select,
        scan_devices,
        set_config,
        set_select,
    )


@app.cell
def __(co, error, get_select, json, requests, time):
    #
    # Device interface
    #
    def enable(state):
        data['output'] = state
        requests.get(f"http://{get_select()}/rpc/Switch.Set?id=0&on={str(bool(state)).lower()}")

    def _updater():
        status = requests.get(f"http://{get_select()}/rpc/Switch.GetStatus?id=0")
        if status.status_code == 200:
            data = json.loads(status.text.encode())
            data['time'] = time.time()
            return data
        else:
            error(f"_updater(): status_code = {status.status_code}")
            return None
    data = {}
    def _archiver(x):
        if x:
            global data
            data = x
            if not 'time' in data:
                data['time'] = time.time()

    feed = co.Collector(poller = _updater,
                        freq = 1, 
                        start = True,
                        archive = _archiver,
                       )
    _archiver(_updater())
    return data, enable, feed


@app.cell
def __(DEBUG, dt, os, sys):
    #
    # Logging
    #

    def stderr(mtype,msg):
        print(f"{mtype} [{os.path.basename(sys.argv[2])}@{dt.datetime.now()}]: {msg}",file=sys.stderr)

    def error(msg):
        # TODO: replace this with logger
        stderr("ERROR",msg)

    def debug(msg):
        # TODO: replace this with logger
        if DEBUG in globals() and DEBUG:
            stderr("DEBUG",msg)
    return debug, error, stderr


@app.cell
def __():
    #
    # App setup
    #
    import sys, os
    import marimo as mo
    import collector as co
    import ui_components as ui
    import time
    import datetime as dt
    import numpy as np
    import json
    import requests
    import threading
    _addpath = f"{os.environ['HOME']}/.shelly"
    if not _addpath in sys.path:
        sys.path.append(f"{os.environ['HOME']}/.shelly")
    import shelly_config

    return (
        co,
        dt,
        json,
        mo,
        np,
        os,
        requests,
        shelly_config,
        sys,
        threading,
        time,
        ui,
    )


if __name__ == "__main__":
    app.run()
