"""GISMo Lab data model

The data module defines the Data class, which is used to exchange data between
modules.  The data fields are defined in the module `data_config.py`.
"""

import sys, os
import json
import time
import math
import datetime as dt
from data_config import fields

datetime_fields = []
for field,spec in fields.items():
    if "datetime_format" in spec:
        datetime_fields.append(field)

class DataException(Exception):
    pass

class Data:
    """Data class"""

    # status
    UNKNOWN = "UNKNOWN"
    OK = "OK"
    ERROR = "ERROR"

    def __init__(self,status=None,message=None,**data):
        """Data class constructor

        ARGUMENTS

            status (str) - data record status (default 'UNKNOWN')

            data (dict) - data values
        """
        self.status = status
        self.message = message
        if status == self.OK:
            self.set_data(init=True,**data)
        elif status == self.ERROR:
            self.set_error(**data)
        else:
            self.status = self.UNKNOWN
            self.set_data(init=True,**data)
        # if not "last_update" in data:
        #     self.last_update = time.time()


    def __getitem__(self,name):
        """Get a field value"""
        return getattr(self,name)

    @staticmethod
    def get_fields():
        """Get list of fields"""
        return list(fields)

    def set_error(self,message):
        """Set the error status

        ARGUMENTS

            message (str) - error message to include is data record
        """
        self.status = self.ERROR
        self.data = dict(message=message)

    def set_data(self,init=False,message=None,exception=True,**data):
        """Set the data

        ARGUMENTS

            init (bool) - flag to indicate whether missing fields should be set to initial value

            message (str) - message to include with the data (default is None)

            data (dict) - data values

        RETURN

            bool - True if the value was successfully set; if False `message` will describe the error
        """
        try:
            if init:
                for field,spec in fields.items():
                    if field in data:
                        setattr(self,field,spec['type'](data[field]))
                    elif init:
                        if callable(spec['none']):
                            setattr(self,field,spec['type'](spec['none']()))
                        else:
                            setattr(self,field,spec['type'](spec['none']))
                    else:
                        setattr(self,field,init)
                self.status = self.OK
                if self.message:
                    self.message = str(message)
            else:
                for key,value in data.items():
                    if key in fields:
                        setattr(self,key,value)
                    else:
                        raise DataException(f"field '{key}' is not valid")
                self.status = self.OK
                if self.message:
                    self.message = str(message)
        except Exception as err:
            e_type, e_value, e_trace = sys.exc_info()
            self.status = self.ERROR
            self.message = f"{e_type.__name__}: {e_value}"
            if exception:
                raise
        
        return self.status == self.OK

    def as_dict(self,format=False):
        """Return data as a dictionary

        ARGUMENTS

            format (bool) - flag to enable formatting of values according to
                            data_config.fields spec

        RETURNS

            dict - data values
        """
        if format is True:
            return dict([(x,y['format']%getattr(self,x)) for x,y in fields.items()])
        else:
            return dict([(x,getattr(self,x)) for x in fields])

    def as_json(self):
        """Return data as a JSON string

        RETURNS

            str - data values in JSON format
        """
        return json.dumps(self.as_dict()) 

    def as_html(self,caption=None):
        """Return data as HTML table

        ARGUMENTS

            caption (str or None) - table caption, if any (default is None)

        RETURNS

            str - HTML table
        """
        data = self.as_dict(format=True)
        rows = []
        for name,spec in fields.items():
            if "datetime_format" in spec:
                try:
                    value = dt.datetime.fromtimestamp(int(float(data[name]))).strftime(spec['datetime_format'])
                except:
                    value = f"{data[name]} {spec['unit']}"
                rows.append(f"""<tr><th align=left>{name.replace('_',' ').title()}</th><td colspan=2 align=center>{value}</td></tr>""")
            else:
                rows.append(f"""<tr><th align=left>{name.replace('_',' ').title()}</th><td align=right>{data[name]}</td><td align=left>{spec['unit'] if 'unit' in spec else ''}</td></tr>""")
        caption = f"<caption>{caption}</caption>" if caption else ""
        return f"<table cellpadding=5>{caption}{''.join(rows)}</table>"

    def as_csv(self):
        """Return data as a CSV record

        RETURNS

            str - CSV data
        """
        data = self.as_dict(format=True)
        rows = [','.join([f"""{f'"{x}"' if ',' in x else x}{'_'+fields[x]['unit'] if 'unit' in fields[x] else ''}""" for x in fields])]
        rows.append(','.join([f"{data[name]}" for name in fields]))
        return '\n'.join(rows)

if __name__ == "__main__":

    import unittest

    class TestData(unittest.TestCase):

        def test_init_nan(self):
            """Verify that floats are initialized to NaN"""
            data = Data()
            self.assertEqual(data.status,data.OK)
            for field,spec in fields.items():
                if fields[field]['none'] == 'nan':
                    self.assertTrue(math.isnan(data[field]))

        def test_init_power(self):
            """Verify that floats can set initialized"""
            data = Data(power=1.23)
            self.assertEqual(data.status,data.OK)
            self.assertEqual(data.power,1.23)

        def test_init_time(self):
            """Verify that the timestamp can be initialized"""
            data = Data(timestamp=123456789.012345)
            self.assertEqual(data.timestamp,123456789.012345)

        def test_init_notime(self):
            """Verify that timestamp is initialized to now"""
            data = Data()
            self.assertAlmostEqual(data.timestamp,time.time(),1)

        def test_init_state(self):
            """Verify that device_state can be initialized"""
            data = Data(device_state="ON")
            self.assertEqual(data.device_state,"ON")

        def test_set_value_ok(self):
            """Verify that a value can be set"""
            data = Data()
            data.set_data(power=1.23)
            self.assertEqual(data.status,data.OK)
            self.assertEqual(data.power,1.23)

        def test_set_value_error(self):
            """Verify that setting an invalid value is an error"""
            data = Data()
            data.set_data(nosuch=1.23,exception=False)
            self.assertEqual(data.message,"DataException: field 'nosuch' is not valid")
            self.assertEqual(data.status,data.ERROR)

        def test_dict(self):
            """Verify dict output"""
            data = Data()
            data.set_data(power=1.23)
            self.assertEqual(data.as_dict()['power'],1.23)

        def test_json(self):
            """Verify JSON output"""
            data = Data()
            data.set_data(power=1.23)
            self.assertEqual(json.loads(data.as_json())['power'],1.23)

        def test_html(self):
            """Verify HTML table output"""
            data = Data()
            data.set_data(power=1.23)
            html = data.as_html()
            self.assertTrue(html.startswith("<table"))
            self.assertTrue(html.endswith("</table>"))

        def test_csv(self):
            """Verify CSV table output"""
            data = Data()
            data.set_data(power=1.23)
            csv = [x.split(",") for x in data.as_csv().split("\n")]
            index = list(fields).index('power')
            self.assertEqual(csv[0][index],'power_W')
            self.assertEqual(csv[1][index],'1.2')

    unittest.main()
