"""Device implementation

The Device class implements the interfaces used to communicate with GISMoLab
devices.  Device classes should be derived from this class and implement the
primary device-level interfaces for scanning the network, getting, setting, 
and polling for data.
"""
import sys
from data import Data
import pandas as pd
import time
from device_config import *

class Device:

	# device states
	DS_UNKNOWN = -1
	DS_OFF = 0
	DS_ON = 1

	def __init__(self):

		self.data = Data()
		self.history = None
		# these should be set by the device implementation class
		self.scanner = lambda:None
		self.getter = lambda:None
		self.setter = lambda:None
		self.poller = lambda:None
		self.poll_frequency = 0
		self.poll_thread = None

	def __del__(self):
		if self.poll_thread:
			self.poll_thread._stop()

	@classmethod
	def all_stop(cls):
		# TODO
		return None

	def scan_network(self,*args,**kwargs):
		"""Scan network for devices

		Returns
		-------
			devices (list of str) - list of devices found
		"""
		return [] if not self.scanner else self.scanner(*args,**kwargs)

	def get_data(self,name=None):
		"""Get the latest data

		Returns
		-------
			data (dict) - the latest data
		"""
		return self.data

	def set_data(self,data):
		"""Set the latest data

		Arguments
		---------
			data (dict) - the latest data
		"""
		self.data = Data(Data.OK,**data)
		if not self.history is None:
			data = dict([(x,[y]) for x,y in self.data.as_dict().items()])
			self.history = pd.concat([self.history,pd.DataFrame(data).set_index("last_update")])
			if type(self.aging) in [int,str] and self.aging > 0:
				last = self.history.index.max()-self.aging
				old = self.history.loc[self.history.index<last]
				if len(old) > 0:
					self.history.drop(index=old.index,inplace=True)
	
	def set_history(self,aging=None):
		"""Set the history

		Arguments
		---------
			aging (float) - aging limit of history data (default None)
		"""
		template = dict([(x,[]) for x in self.data.fields.keys()])
		self.history = pd.DataFrame(template).set_index("last_update")
		self.aging = aging

	def get_history(self):
		"""Get the history

		Returns
		-------
			history (pandas.DataFrame) - the historical data record
		"""
		return self.history

	def start_polling(self):
		"""Start polling for data
		"""
		if not self.poller:
			raise DeviceException("no poller specified")
		self.poll_thread = threading.Thread(target=self.poller)
		self.poll_thread.start()
		# TODO: start polling thread
		return

	def stop_polling(self):
		"""Stop polling for data
		"""
		if self.poll_thread:
			self.poll_thread._stop()
		self.poll_frequency = 0
		return

if __name__ == "__main__":
	import unittest

	class TestDevice(unittest.TestCase):
		def test_history_aging(self):
			x = Device()
			x.set_history(aging=60)
			for n in range(100):
				x.set_data({"last_update":time.time()-n,"energy":123.45-n})
			self.assertAlmostEqual(x.get_history()["energy"].min(),63.45)
		def test_history(self):
			x = Device()
			x.set_history()
			for n in range(100):
				x.set_data({"last_update":time.time()-n,"energy":123.45-n})
			self.assertAlmostEqual(x.get_history()["energy"].min(),24.45)
		def test_getdata(self):
			x = Device()
			for n in range(100):
				x.set_data({"last_update":time.time()-n,"energy":123.45-n})
			self.assertAlmostEqual(x.get_data().energy,24.45)
	unittest.main()
