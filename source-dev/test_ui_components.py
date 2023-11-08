import marimo

__generated_with = "0.1.41"
app = marimo.App(width="full")


@app.cell
def __(mo):
    #
    # Progress state
    #
    get_progress, set_progress = mo.state(0)
    return get_progress, set_progress


@app.cell
def __(mo):
    #
    # Refresh control
    #
    refresh = mo.ui.refresh([1,2,5,10,30,60],1)
    mo.hstack([mo.md("Refresh: "),refresh],justify="start")
    return refresh,


@app.cell
def __(
    get_progress,
    mo,
    refresh,
    reset_progress,
    resume_progress,
    start_progress,
    stop_progress,
    threads,
    ui_components,
):
    #
    # Progress view
    #
    refresh
    fig = ui_components.GoIndicator(
        mode = "gauge+number",
        value = get_progress(),
        domain = {'x': [0, 1], 'y': [0, 1]},
        gauge = {'axis':{'range':[0,100]}},
        title = {'text': "Progress"})
    start = mo.ui.button(label="Start" if get_progress() in [0,100] else "Continue",
                         disabled=bool(len(threads)!=0) or get_progress() == 100,
                         on_click=start_progress if get_progress() == 0 else resume_progress)
    stop = mo.ui.button(label="Stop",
                        disabled=bool(len(threads)==0),
                        on_click=stop_progress)
    reset = mo.ui.button(label="Reset",
                         disabled=bool(get_progress()==0),
                         on_click=reset_progress)
    mo.vstack([fig.get_figure(),mo.hstack([start,stop,reset],justify="center")])

    return fig, reset, start, stop


@app.cell
def __(get_progress, set_progress, threading, threads, time):
    #
    # Progress update
    #
    def progress_update():
        while len(threads) > 0:
            if get_progress() < 100:
                set_progress(get_progress()+10)
            else:
                del threads[0]
                break
            time.sleep(1)

    def stop_progress(value):
        while len(threads) > 0:
            thread = threads[0]
            del threads[0]
            thread.join()

    def resume_progress(value):
        if len(threads) == 0:
            threads.append(threading.Thread(target=progress_update))
            threads[0].start()

    def start_progress(value):
        reset_progress(0)
        resume_progress(0)

    def reset_progress(value):
        set_progress(0)

    return (
        progress_update,
        reset_progress,
        resume_progress,
        start_progress,
        stop_progress,
    )


@app.cell
def __():
    #
    # Setup
    #
    import marimo as mo
    import time
    import ui_components
    import threading
    threads = []
    return mo, threading, threads, time, ui_components


if __name__ == "__main__":
    app.run()
