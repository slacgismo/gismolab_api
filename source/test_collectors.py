import marimo

__generated_with = "0.1.42"
app = marimo.App()


@app.cell
def __(co):
    datetime_format = "at %H:%M:%S on %m/%d/%y"
    initial_refresh = 1
    co.DEBUG = False
    return datetime_format, initial_refresh


@app.cell
def __(archive, datetime_format, dt, feed, mo, refresh, ui):
    refresh
    _time = max(archive.keys())
    _value = archive[_time]
    _gauge = ui.GoIndicator(
                    mode = "gauge+number",
                    value = round(_value,0),
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    gauge = {'axis':{'range':[0,100]}},
                    title = {'text': "Random walk"})
    start = mo.ui.button(label = "Start",
                         on_click = lambda _:feed.set_freq(1),
                         disabled = feed.is_polling())
    stop = mo.ui.button(label = "Stop",
                        on_click = lambda _:feed.stop_polling(),
                        disabled = not feed.is_polling())
    mo.vstack([_gauge.get_figure(),
               mo.hstack([
                   mo.md("Polling control:"),start,stop],justify="start"),
                   mo.md(f"Polling is {f'every {feed.freq} second' if feed.is_polling() else 'off'}."),
                   mo.md(f"{len(archive)} samples have been received."),
                   mo.md(f"The last value received {dt.datetime.fromtimestamp(_time).strftime(datetime_format)} is {_value:.2f}"),])
    return start, stop


@app.cell
def __(initial_refresh, mo):
    refresh = mo.ui.refresh([1,2,5,10],initial_refresh)
    mo.hstack([mo.md("The screen update rate is "),refresh],justify="start")
    return refresh,


@app.cell
def __(archive, co, mo, np, time):
    _get_value,_set_value = mo.state(50.0)
    def _updater():
        _set_value(min(100,max(0,_get_value()+np.random.normal(0,1))))
        return _get_value()
    def _archiver(x):
        archive[time.time()] = x
    feed = co.Collector(poller = _updater,
                        freq = 1, 
                        start = True,
                        archive = _archiver,
                       )
    return feed,


@app.cell
def __():
    import marimo as mo
    import collector as co
    import ui_components as ui
    import time
    import datetime as dt
    import numpy as np
    archive = {}
    return archive, co, dt, mo, np, time, ui


if __name__ == "__main__":
    app.run()
