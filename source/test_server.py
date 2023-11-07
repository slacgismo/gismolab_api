import marimo

__generated_with = "0.1.43"
app = marimo.App(width="full")


@app.cell
def __():
    #
    # App configuration
    #
    datetime_format = "at %H:%M:%S on %m/%d/%y"
    initial_refresh = None
    config_update_freq = 10
    server_host = "127.0.0.1"
    server_port = 5000
    DEBUG = True
    # co.DEBUG = False
    return (
        DEBUG,
        config_update_freq,
        datetime_format,
        initial_refresh,
        server_host,
        server_port,
    )


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

    # data
    print(data)
    try:
        _time = data['time']
        name = str(device_config["name"])
        power = float(data["power"])
        energy = float(data["energy"])
        control = (data["device_state"] == "ON")
        _status = f"Status: Device {'on' if control else 'off'}"
    except Exception as err:
        _time = time.time()
        name = ""
        power = 0.0
        energy = 0.0
        control = False
        _status = f"Status: Error -- {err}"
    _power = ui.GoIndicator(mode = "gauge+number",
                            value = round(power/1000,1),
                            domain = {'x': [0, 1], 'y': [0, 1]},
                            gauge = {'axis':{'range':[0,2.0]}},
                            title = {'text': f"{name} Power (kW)"},
                           )
    _energy = ui.GoIndicator(mode = "gauge+number",
                             value = round(energy/1000,1),
                             domain = {'x': [0, 1], 'y': [0, 1]},
                             gauge = {'axis':{'range':[0,100]}},
                             title = {'text': f"{name} Energy (kWh)"},
                            )
    _age = time.time() - _time
    _age = f"Data age: {_age:.3f} seconds"

    # layout
    tabs = mo.tabs({"Power":_power.get_figure(),"Energy":_energy.get_figure()})
    select = mo.ui.dropdown(options=device_names,value=device_config['name'],on_change=change_select)
    switch = mo.ui.switch(value=control,on_change=enable)
    rescan = mo.ui.button(label="Refresh",on_click=scan_devices)

    mo.vstack([mo.hstack([mo.md("Device:"),select,rescan],justify="start"),
               # mo.hstack([_power.get_figure(),_energy.get_figure()]), 
               tabs,
               mo.hstack([
                   mo.hstack([
                       mo.md("Device enable:"),
                       switch],justify="start"),
                   mo.md(_age),
               ]),
               mo.md(_status),
              ])
    return control, energy, name, power, rescan, select, switch, tabs


@app.cell
def __(err, error, mo, server_get):
    #
    # Device list
    #

    device_names = None
    device_labels = None
    device_config = None

    def scan_devices():
        try:
            data = server_get("plugs")
            global device_names
            device_names = dict((x.replace('_',' ').title(),x) for x in data)
            global device_labels
            device_labels = dict([(y,x) for x,y in device_names.items()])
        except Exception as err:
            error(f"scan_devices(): {err}")

    get_select,set_select = mo.state(None)

    def change_select(name):
        set_select(name)

        global device_config
        device_config = {"name":device_labels[name]}

    scan_devices()
    if device_labels:
        change_select(list(device_labels.keys())[0])
    return (
        change_select,
        device_config,
        device_labels,
        device_names,
        get_select,
        scan_devices,
        set_select,
    )


@app.cell
def __(co, err, error, get_select, server_get, start, time):
    #
    # Device interface
    #
    def enable(state):
        data['power_control'] = state
        try:
            server_get("plug",get_select(),'on' if state else 'off')
        except Exception as err:
            error(f"enable(state={start}): {err}")

    def _updater():
        try:
            data = server_get("plug",get_select())
            if 'time' not in data:
                data['time'] = time.time()
            return data
        except Exception as err:
            error(f"_updater(): {err}")
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
def __(debug, json, requests, server, server_host, server_port, threading):
    #
    # Server startup
    #
    threading.Thread(target=lambda:server._app.run(host=server_host,port=server_port)).start()
    server_url = f"http://{server_host}:{server_port}"
    def server_get(*args,**kwargs):
        req = requests.get(f"{server_url}/{'/'.join(args)}?{'&'.join([f'{x}={y}' for x,y in kwargs.items()])}")
        if req.status_code == 200:
            debug(f"server_get(*args={args},**kwargs={kwargs}) --> {req.text}")
            return json.loads(req.text.encode())
        raise Exception(f"HTTP error code {req.status_code}")

    return server_get, server_url


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
    import requests
    import json
    import server
    import threading

    return co, dt, json, mo, os, requests, server, sys, threading, time, ui


if __name__ == "__main__":
    app.run()
