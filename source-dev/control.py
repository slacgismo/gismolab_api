import marimo

__generated_with = "0.1.39"
app = marimo.App()


@app.cell
def __(mo, server, sp, threading, time):
    #
    # Data collector and UI refresh
    #

    update_freq = 1.0 # seconds

    # Shelly plug updater
    get_shelly_data, set_shelly_data = mo.state(0)
    def shelly_updater():
        while True:
            set_shelly_data(sp.poll_data)
            time.sleep(update_freq)
    shelly_thread = threading.Thread(target=shelly_updater)
    shelly_thread.start()

    # Powerflex controller updater
    get_powerflex_data, set_powerflex_data = mo.state(server._powerflex_update(duration=update_freq*10))
    def powerflex_updater(freq=update_freq):
        while True:
            global powerflex_data
            set_powerflex_data(server._powerflex_update(duration=freq*2))
            time.sleep(freq)
    powerflex_thread = threading.Thread(target=powerflex_updater)
    powerflex_thread.start()

    # UI refresh rate control
    refresh = mo.ui.refresh([f"{x}s" for x in [1,2,5,10,30,60]],default_interval="5s")
    refresh
    return (
        get_powerflex_data,
        get_shelly_data,
        powerflex_thread,
        powerflex_updater,
        refresh,
        set_powerflex_data,
        set_shelly_data,
        shelly_thread,
        shelly_updater,
        update_freq,
    )


@app.cell
def __(evchargers, mo, switches):
    #
    # UI display
    #
    mo.tabs({"EV Chargers":evchargers,"Plugs":switches})
    return


@app.cell
def __(get_powerflex_data, keys, mo):
    powerflex_data = get_powerflex_data()
    def powerflex_meter(acc_id,acs_id):
        data = powerflex_data.loc[(acc_id,acs_id)]
        last = data.loc[data.index.get_level_values(0).unique().max()]
        return mo.md(f"""
            <table cellpadding=5>
                <caption>Charger {acc_id}-{acs_id}<hr/></caption> 
                <tr><th align=left>Meter</th><td align=right>{last.energy_delivered/1e6:.1f}</td><td>kWh</td></tr>
                <tr><th align=left>Power</th><td align=right>{last.power/1e6:.1f}</td><td>kW</td></tr>
                <tr><th align=left>Current</th><td align=right>{last.mamps_actual/1e3:.1f}</td><td>A</td></tr>
                <tr><th align=left>Voltage</th><td align=right>{last.voltage/1e3:.1f}</td><td>V</td></tr>
                <tr><th align=center>Charger mode</th><td align=right colspan=2>{last.charging_state}</td></tr>
            </table>""")

    items = dict([(x,list(powerflex_data.loc[x].index.get_level_values(0).unique().sort_values())) for x in powerflex_data.index.get_level_values(0).unique()])

    powerflex_keys = []
    for key,values in items.items():
        for value in values:
            keys.append((key,value))
    evchargers = mo.vstack([mo.md(f"## Powerflex controllers"),mo.hstack([powerflex_meter(*x) for x in powerflex_keys],justify="space-around")])

    return (
        evchargers,
        items,
        key,
        powerflex_data,
        powerflex_keys,
        powerflex_meter,
        value,
        values,
    )


@app.cell
def __(get_shelly_data, mo, refresh, sp):
    #
    # Switches display content
    #
    refresh
    result = []
    def shelly_settings(name,data):
        return f"""<a href="http://{sp.config[name]['ipaddr']}/#/settings/schedules/0" target=_blank>Settings</a> ({len(data['jobs'])})"""

    for name, data in get_shelly_data().items():
        switch = mo.ui.switch(data['status']['output'],on_change=lambda x:sp.set_switch(name,x))
        result.append(
            mo.md(f"""<table>
                <caption><nobr>{data['config']['name']}</nobr><hr/></caption>
                <tr><th align=left>Switch</th><td colspan=2>{switch}</td></tr>
                <tr><th align=left>Power</th><td align=right>{data['status']['apower']/1000:.1f}</td><td align=left>kW</td></tr>
                <tr><th align=left>Voltage</th><td align=right>{data['status']['voltage']:.1f}</td><td align=left>V</td></tr>
                <tr><th align=left>Current</th><td align=right>{data['status']['current']:.1f}</td><td align=left>A</td></tr>
                <tr><th align=left>Energy</th><td align=right>{data['status']['aenergy']['total']/1000:.1f}</td><td align=left>kWh</td></tr>
                <tr><td colspan=3 align=left>{shelly_settings(name,data)}</td></tr>
            </table>
            """
            )
        )
    switches = mo.vstack([mo.md("## Shelly Plugs"),mo.hstack(result, justify="space-between")])
    return data, name, result, shelly_settings, switch, switches


@app.cell
def __():
    #
    # Initialization
    #
    import marimo as mo
    import time
    import threading
    import powerflex as pf
    import sonnen as sb
    import egauge as eg
    import shelly as sp
    import server

    sp.start_polling(1)
    None
    return eg, mo, pf, sb, server, sp, threading, time


if __name__ == "__main__":
    app.run()
