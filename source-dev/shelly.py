"""Shelly device interface

"""
import os, sys
try:
    import requests
    import json
    import threading
    import time
    import asyncio
    import aiohttp
    import socket, netifaces
    from device import Device
except:
    os.system("python3 -m pip install -r ../requirements.txt")

sys.path.insert(0,os.path.join(os.environ["HOME"],".shelly"))

device_ipaddr = []
device_timeout = 1.0
poll_frequency = 10.0
verbose_enable = False
max_scan = 256
try:
    from shelly_config import *
except:
    pass

class Shelly(Device):

    device_list = []

    def __init__(self):

        Device.__init__(self)

config = {}
data = {}

# try:
#     from shelly_access import *
# except:
#     print(f"ERROR [shelly]: shelly_access.py not found in sys.path - using default access credentials")

def verbose(msg):
    """Verbose output

    Arguments
    ---------

        msg (str) - output message
    """        
    if verbose_enable:
        print(f"VERBOSE [shelly]: {msg}",file=sys.stderr)


#
# Network scanner
#
scan_result = []
async def _scan_task(name, work_queue):
    """Scan task

    Arguments
    ---------
        name (str) - device name

        work_queue (asyncio.Queue) - work queue
    """
    async with aiohttp.ClientSession(connector = aiohttp.TCPConnector(limit=max_scan)) as session:
        while not work_queue.empty():
            url = await work_queue.get()
            verbose(f"{name}: GET {url}")
            try:
                async with session.get(url,timeout=device_timeout) as response: 
                    _device_found(name,url,await response.text())
            except Exception as err:
                pass

def _device_found(name,url,response,**kwargs):
    """Device found

    Arguments
    ---------
        name (str) - device name

        url (str) - url found

        response (dict) - response data
    """    
    try:
        data = json.loads(response)
        if data["id"].startswith("shelly"):
            scan_result.append(name)
            verbose(f"found {name} at {url} - result = {data}")
        else:
            verbose(f"device at {url} is not a Shelly - response = {data}")
    except:
        verbose(f"device at {url} is not a Shelly - response = {data}")

async def _scanner(networks):
    """Scanner

    Arguments
    ---------
        networks (list) - list of network search ranges
    """
    work_queue = asyncio.Queue()
    iplist = []
    tasks = []
    for iprange in networks:
        start,stop = [[int(y) for y in x.split(".")] for x in iprange.split("-")]
        for d in range(start[0],stop[0]+1):
            for c in range(start[1],stop[1]+1):
                for b in range(start[2],stop[2]+1):
                    for a in range(start[3],stop[3]+1):
                        ipaddr = f"{d}.{c}.{b}.{a}"
                        iplist.append(ipaddr)

    for n in range(0,len(iplist),max_scan):
        for ipaddr in iplist[n:n+max_scan]:
            verbose(f"QUEUE: {ipaddr}")
            await work_queue.put(f"http://{ipaddr}/shelly")
        for ipaddr in iplist:
            tasks.append(asyncio.create_task(_scan_task(ipaddr,work_queue)))
        await asyncio.gather(*tasks)

def scan_network(networks = [],save=False):
    """Scan for Shelly devices

    Arguments
    ---------
        format (str) - specify format of return value

    Returns
    -------
        (list) - if `format` is 'list' (default)

        (dict) - if `format` is 'name' or 'addr', which selects key vlaue
        
        (str) - if format is 'csv' or 'table', which determines whether header
                row is included
        
        (pandas.DataFrame) - if format is 'pandas'

    Exceptions
    ----------
        Various - Exceptions from pandas, netifaces, requests, etc.
    """
    if not networks:
        networks = []
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8',80)) # use google to create a working socket without sending anything
        ipaddr = s.getsockname()[0]
        iflist = netifaces.interfaces()
        for iface in iflist:
            spec = netifaces.ifaddresses(iface)
            if netifaces.AF_INET in spec:
                for addrs in spec[netifaces.AF_INET]:
                    if addrs['addr'] == ipaddr:
                        ipmask = addrs['netmask']
                        ipcast = addrs['broadcast']
                        if ipcast.endswith(".255.255") and not LONGSCAN:
                            raise Exception("long scan is not enabled")
                        verbose(f"host ipaddr = {ipaddr}, netmask = {ipmask}, broadcast = {ipcast}")
                        networks.append(ipcast.replace("255","0") + "-" + ipcast)
    asyncio.run(_scanner(networks))
    if save:
        global device_ipaddr
        device_ipaddr = scan_result
        if type(save) is str:
            with open(save,"w") as fh:
                fh.write(f"""
device_ipaddr = {device_ipaddr}
device_timeout = {device_timeout}
""")
    return scan_result

#
# Device access
#
def init_devices(network=[],autoscan=True):
    """Init devices

    Arguments
    ---------
        network (list of str) - list of network ip ranges to scan

        autoscan (bool) - scan for devices automatically if none configured
    """
    threads = []
    global device_ipaddr
    if not device_ipaddr and autoscan:
        device_ipaddr = scan_network(network)
    for ipaddr in device_ipaddr:
        def init_device():
            try:
                verbose(f"Trying {ipaddr}...")
                reply = requests.get(f"http://{ipaddr}/shelly",timeout=device_timeout)
                if reply.status_code == 200:
                    data = json.loads(reply.text.encode())
                    data["ipaddr"] = ipaddr
                    if data["name"]:
                        config[data["name"]] = data
                    verbose("ok")
                else:
                    verbose(f"error {reply.status_code}")
            except Exception as err:
                verbose(f"exception {err}")
        thread = threading.Thread(target=init_device)
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
    verbose(config)

def get_devices():
    """Get devices

    Returns
    -------
        Device configurations (dict)
    """
    if not config:
        init_devices()
    return config

def get_device_list():
    """Get device list

    Returns
    -------
        List of device names (list of str)
    """
    return list(get_devices().keys())

def get_device_data(device):
    """Get device data

    Arguments
    ---------
        device (str) - device name

    Returns
    -------
        data (dict) - device data
            config (dict) - configuration data
            status (dict) - status data
            jobs (dict) - jobs data
    """
    data = get_devices()[device]
    ipaddr = data["ipaddr"]
    result = {}

    try:
        reply = requests.get(f"http://{ipaddr}/rpc/Switch.GetConfig?id=0",timeout=device_timeout)
        result["config"] = json.loads(reply.text.encode())
    except Exception as err:
        result["config"] = {"status_code":reply.status_code, "error":str(err)}
    
    try:
        reply = requests.get(f"http://{ipaddr}/rpc/Switch.GetStatus?id=0",timeout=device_timeout)
        result["status"] = json.loads(reply.text.encode())
    except Exception as err:
        result["status"] = {"status_code":reply.status_code, "error":str(err)}

    try:
        reply = requests.get(f"http://{ipaddr}/rpc/Schedule.List",timeout=device_timeout)
        result["jobs"] = json.loads(reply.text.encode())
    except Exception as err:
        result["jobs"] = {"status_code":reply.status_code, "error":str(err)}


    return result

def get_data():
    """Get data

    Returns
    -------
        data (dict) - device data by name
    """
    if not get_devices():
        return {"error":"no devices configured"}

    result = {}
    for name in get_device_list():
        result[name] = get_device_data(name)

    return result

def set_switch(device,state):
    """Set switch

    Arguments
    ---------
        device (str) - device name

        state (bool) - switch state

    Returns
    -------

        previous value (bool) - None on failure
    """
    data = get_devices()[device]
    ipaddr = data["ipaddr"]
    # print(f"{device}.state = ({type(state)}) {state}",file=sys.stderr)
    value = str(bool(state)).lower()
    reply = requests.get(f"http://{ipaddr}/rpc/Switch.Set?id=0&on={value}")
    if reply.status_code == 200 and device in poll_data:
        poll_data[device]['status']['output'] = state
        return reply.text
    else:
        return None

def all_stop():
    """All stop

    Returns
    -------
        devices (list) - list of devices stopped successfully
    """
    threads = {}
    stopped = []
    def stop(device):
        set_switch(device,False)
        stopped.append(device)
    for device in get_devices():
        thread = threading.Thread(target=lambda:stop(device))
        thread.start()
        threads[device] = thread
    for device,thread in threads.items():
        thread.join()
    return stopped


#
# Polling
#
poll_threads = {}
poll_data = {}

def start_polling(freq=poll_frequency):
    """Start polling

    Arguments
    ---------
        freq (float) - polling frequency in seconds

    Returns
    -------
        thread list (list) - list of polling threads
    """
    if not poll_threads:
        for device in get_devices().keys():
            poll_data[device] = get_device_data(device)
            def poll_function():
                while True:
                    try:
                        poll_data[device] = get_device_data(device)
                    except:
                        pass
                    time.sleep(poll_frequency)
            thread = threading.Thread(target=poll_function)
            thread.start()
            poll_threads[device] = thread
    return poll_threads

def stop_polling():
    """Stop polling
    """
    for thread in poll_threads.values():
        del thread

def poll_status():
    """Poll status

    Returns
    -------
        Thread status (dict) - thread status data
    """
    return dict([(x,y.is_alive()) for x,y in poll_threads.items()])

if __name__ == "__main__":

    init_devices()
    print(get_data(),flush=True)

    print(start_polling(1),flush=True)
    print(poll_status(),flush=True)
    time.sleep(1)
    print(poll_data,flush=True)
