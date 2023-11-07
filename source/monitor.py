import marimo

__generated_with = "0.1.39"
app = marimo.App(width="full")


@app.cell
def __(mo):
    update_freq = 10
    refresh = mo.hstack([mo.md("Refresh: "),mo.ui.refresh([f"{update_freq}s"],default_interval=f"{update_freq}s")],justify="start")
    mo.hstack([mo.md(f"# GISMo Lab Monitor"),refresh])
    return refresh, update_freq


@app.cell
def __(batteries, evchargers, meters, mo, refresh, switches):
    refresh
    mo.tabs({"EV Chargers":evchargers,"Batteries":batteries,"Meters":meters,"Switches":switches})
    return


@app.cell
def __(err, get_powerflex_data, mo):
    try:
        powerflex_data = get_powerflex_data()
        def powerflex_meter(acc_id,acs_id):
            data = powerflex_data.loc[(acc_id,acs_id)]
            last = data.loc[data.index.get_level_values(0).unique().max()]
            return mo.md(f"""
                <table cellpadding=10>
                    <caption>Charger {acc_id}-{acs_id}<hr/></caption> 
                    <tr><th align=left>Meter</th><td align=right>{last.energy_delivered/1e6:.1f}</td><td>kWh</td></tr>
                    <tr><th align=left>Power</th><td align=right>{last.power/1e6:.1f}</td><td>kW</td></tr>
                    <tr><th align=left>Current</th><td align=right>{last.mamps_actual/1e3:.1f}</td><td>A</td></tr>
                    <tr><th align=left>Voltage</th><td align=right>{last.voltage/1e3:.1f}</td><td>V</td></tr>
                    <tr><th align=center>Charger mode</th><td align=right colspan=2>{last.charging_state}</td></tr>
                </table>""")
        
        items = dict([(x,list(powerflex_data.loc[x].index.get_level_values(0).unique().sort_values())) for x in powerflex_data.index.get_level_values(0).unique()])
        
        keys = []
        for key,values in items.items():
            for value in values:
                keys.append((key,value))
        evchargers = mo.vstack([mo.md(f"## EV Chargers"),mo.hstack([powerflex_meter(*x) for x in keys],justify="space-around")])
    except Exception as err:
        evchargers = mo.md(f"ERROR: {err}")
    return (
        evchargers,
        items,
        key,
        keys,
        powerflex_data,
        powerflex_meter,
        value,
        values,
    )


@app.cell
def __(mo, server, time, update_freq):
    get_powerflex_data, set_powerflex_data = mo.state(server._powerflex_update(duration=update_freq*2))

    def powerflex_updater(freq=update_freq):
        while True:
            global powerflex_data
            set_powerflex_data(server._powerflex_update(duration=freq*2))
            time.sleep(freq)

    import threading
    updater = threading.Thread(target=powerflex_updater)
    updater.start()
    return (
        get_powerflex_data,
        powerflex_updater,
        set_powerflex_data,
        threading,
        updater,
    )


@app.cell
def __(err, mo, sb):
    try:
        sonnen_data = sb.SonnenInterface().get_status()
        battery_mode_label = {
            "FlowConsumptionBattery" : "BATTERY TO LOAD",
            "FlowConsumptionGrid" : "GRID TO LOAD",
            "FlowConsumptionProduction": "GENERATION TO LOAD",
            "FlowGridBattery" : "BATTERY TO GRID",
            "FlowProductionBattery" : "GENERATION TO BATTERY",
            "FlowProductionGrid" : "GENERATION TO GRID",
        }
        battery_mode = "<BR/>".join([battery_mode_label[x] for x,y in sonnen_data.items() if x.startswith("Flow") and y is True])
        batteries = mo.vstack([mo.md("## Batteries"),
            mo.md(f"""<table cellpadding=10>
                <caption>Sonnen<HR/></caption>
                <tr><th align=left valign=top>Battery Mode</th><td align=center colspan=2>Mode {sonnen_data['OperatingMode']}<BR/>{battery_mode}</td></tr>
                <tr><th align=left>Battery power</th><td align=right>{sonnen_data['Pac_total_W']/1000}</td><td>kW</td></tr>
                 <tr><th align=left>Battery capacity</th><td align=right>{sonnen_data['RemainingCapacity_Wh']/1000}</td><td>kWh</td></tr>
                <tr><th align=left>State of Charge</th><td align=right>{sonnen_data['USOC']}</td><td>%</td></tr>
                 <tr><th align=left>Backup buffer</th><td align=right>{sonnen_data['BackupBuffer']}</td><td>%</td></tr>
            </table>
        """)])
    except Exception as err:
        batteries = mo.md(f"ERROR: {err}")  
    return batteries, battery_mode, battery_mode_label, sonnen_data


@app.cell
def __(eg, err, mo):
    try:
        meter_data = eg.EgaugeInterface().processing_egauge_data()
        meters = mo.vstack([mo.md("## Meters"),
            mo.md(f"""<table cellpadding=10>
                <caption>House A<HR/></caption>
                <tr><th align=left>Subpanel</th><td align=right>{meter_data['A.SubPanel']}</td><td>kW</td></tr>
                <tr><th align=left>Grid power</th><td align=right>{meter_data['A.GridPower']}</td><td>kW</td></tr>
                <tr><th align=left>Solar</th><td align=right>{meter_data['A.Solar']}</td><td>kW</td></tr>
                <tr><th align=left>EV charter</th><td align=right>{meter_data['A.EV']}</td><td>kW</td></tr>
                <tr><th align=left>Battery</th><td align=right>{meter_data['A.Battery']}</td><td>kW</td></tr>
            </table>
        """)])
    except Exception as err:
        meters = mo.md(f"ERROR: {err}")  
    return meter_data, meters


@app.cell
def __(mo, sp, sys):
    try:
        switch_data = sp.get_data()
        switches = []
        for switch,data in switch_data.items():
            switches.append(mo.md(f"""<table cellpadding=10>
                <caption><nobr>{data['config']['name']}</nobr><hr/></caption>
                <tr><th align=left>State</th><td colspan=2 align=center>{'ON' if data['status']['output'] else 'OFF'}</td></tr>
                <tr><th align=left>Meter</th><td align=right>{data['status']['aenergy']['total']/1000:.1f}</td><td>kWh</td></tr>
                <tr><th align=left>Power</th><td align=right>{data['status']['apower']/1000:.1f}</td><td>kW</td></tr>
                <tr><th align=left>Voltage</th><td align=right>{data['status']['voltage']:.1f}</td><td>V</td></tr>
                <tr><th align=left>Current</th><td align=right>{data['status']['current']:.1f}</td><td>V</td></tr>
                </table>"""))
        switches = mo.vstack([mo.md("## Switches"),
                              mo.hstack(switches,justify="space-around")])
    except Exception as err:
        e_type, e_value, e_trace = sys.exc_info()    
        switches = mo.md(f"ERROR: {e_type.__name__} {e_value} {e_trace}")  
    return data, e_trace, e_type, e_value, switch, switch_data, switches


@app.cell
def __(time):
    cache_expire = 60
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
    return age_cache, cache, cache_expire, get_cache, set_cache


@app.cell
def __():
    status = {
    	"powerflex" : {
    		"status" : "UNKNOWN",
    		"last_update" : None,
    	},
    }
    return status,


@app.cell
def __(pf):
    pf_token = pf.perform_login(pf.URLS["SLAC"]["LOGIN"], pf.username,pf.password)
    pf_auth_headers = pf.set_authentication_headers(pf_token)
    return pf_auth_headers, pf_token


@app.cell
def __():
    import marimo as mo
    import time
    import datetime as dt
    import powerflex as pf
    import sonnen as sb
    import egauge as eg
    import shelly as sp
    import server
    return dt, eg, mo, pf, sb, server, sp, time


if __name__ == "__main__":
    app.run()
