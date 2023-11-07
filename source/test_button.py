import marimo

__generated_with = "0.1.39"
app = marimo.App()


@app.cell
def __(getter, mo, setter):
    button = mo.ui.button(label="Hit me!",kind="danger",on_click=lambda x:setter(getter()+1))
    button
    return button,


@app.cell
def __(getter):
    getter()
    return


@app.cell
def __():
    import marimo as mo
    getter,setter = mo.state(0)
    return getter, mo, setter


if __name__ == "__main__":
    app.run()
