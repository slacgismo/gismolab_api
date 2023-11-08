import marimo

__generated_with = "0.1.38"
app = marimo.App(width="full")


@app.cell
def __():
    #
    # Configuration settings
    #

    # Default refresh frequency (see refresh)
    default_refresh = None

    # Default server URL
    server_url = "http://127.0.0.1:5000"

    # Tabs to display and query names
    tabs = {
        "Chargers": "evcharger",
        "Meters": "meter",
        "Batteries": "battery",
        "HVAC": "hvac",
        "Hotwater": "waterheater",
        "Plugs": "plug",
    }
    return default_refresh, server_url, tabs


@app.cell
def __(default_refresh, emergency_stop, mo, scan_network):
    #
    # Create UI refresh
    #
    refresh = mo.ui.refresh(options=[1,2,5,10,30,60],default_interval=default_refresh)
    mo.hstack([
        mo.hstack([mo.md("Display refresh: "),refresh],justify="start"),
        mo.hstack([
            mo.ui.button(label="Scan network",on_click=scan_network),
            mo.ui.button(label="ALL STOP!",kind="danger",on_click=emergency_stop)
        ])
    ],justify="space-between")    
    return refresh,


@app.cell
def __(getset, mo, refresh, tabs):
    #
    # Main UI
    #
    refresh
    mo.vstack([
        mo.md("## Devices"),
        mo.tabs(dict([(x,getset[y][0]()) for x,y in tabs.items()]))
    ])
    return


@app.cell
def __(
    default_refresh,
    get_content,
    mo,
    pd,
    refresh,
    tabs,
    threading,
    threads,
    time,
):
    #
    # Device polling
    #
    threads
    getset = dict([(y,mo.state(get_content(y))) for x,y in tabs.items()])
    def create_updater(name,getset):
        def updater():
            while True: 
                getset[name][1](get_content(name))
                try:
                    dtime = pd.Timedelta(refresh.value.split()[0]).total_seconds()
                except:
                    dtime = default_refresh
                time.sleep(dtime if dtime>0 else 1e6)
        return updater
    if not threads:
        threads.extend([threading.Thread(target=create_updater(x,getset)) for x in tabs.values()])
    mo.md(f"Status: {len(threads)} polling threads active")
    return create_updater, getset


@app.cell
def __(server_url):
    #
    # Support and utilities
    #
    import marimo as mo
    import requests
    import json
    import threading
    import time
    import pandas as pd

    threads = []

    def get_content(source):
        try:
            devices = json.loads(requests.get(f"{server_url}/{source}s").text)
            result = mo.hstack([mo.md(requests.get(f"{server_url}/{source}/{x}?format=html").text) for x in devices])
        except Exception as err:
            result = mo.md(f"Nothing available")
        return result

    def emergency_stop(*args,**kwargs):
        requests.get(f"{server_url}/stop")

    def scan_network(*args,**kwargs):
        requests.get(f"/shelly/scan")
        threads = []
    return (
        emergency_stop,
        get_content,
        json,
        mo,
        pd,
        requests,
        scan_network,
        threading,
        threads,
        time,
    )


if __name__ == "__main__":
    app.run()
