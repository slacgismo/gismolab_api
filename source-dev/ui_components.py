import plotly.graph_objects as go
import requests
import threading
import collector

class UiComponentException(Exception):
    pass

class GoIndicator:

    def __init__(self,**kwargs):
        self.config = kwargs
        self.fig = self.get_figure()
        self.thread = None
        self.freq = None

    def get_figure(self):
        return go.Figure(go.Indicator(**self.config))

    def start_polling(self,source,freq,parser=None,replace=True):
        if self.thread != None and not replace:
            raise UiComponentException("polling is already started")
        if self.freq <= 0:
            raise UiComponentException("update frequency must be stricly positive")
        if type(source) != Collector:
            raise UiComponentException("source is not a collector")
        if not parser and not hasattr(source,"value"):
            raise UiComponentException("source does not have a 'value' attribute")
        def updater(self):
            if self.freq == None:
                return
            self.config['value'] = parser(self.source) if parser else self.source.value
            time.sleep(self.freq)
        self.freq = freq
        self.thread = threading.Thread(target=lambda:updater(self))
        self.thread.start()

    def stop_polling(self,ignore=True):
        if self.thread == None and not ignore:
            raise UiComponentException("polling was not started")
        self.freq = None
        self.thread.join()

    def set_value(self,value):
        self.config["value"] = value

    def get_value(self):
        return self.config["value"]

if __name__ == "__main__":

    import unittest

    class TestIndicator(unittest.TestCase):

        def test_indicator(self):
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = 0,
                domain = {'x': [0, 1], 'y': [0, 1]},
                gauge = {'axis':{'range':[0,100]}},
                title = {'text': "Test"}))
            self.assertTrue(fig!=None)

    unittest.main()