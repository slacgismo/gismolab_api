
# Pubsub Config
ENDPOINT = "ahj7dwf3rk9hf-ats.iot.us-west-1.amazonaws.com"
CLIENT_ID = "HouseB"
CLIENT_ID_CONTROL = "DER_Controller"
CLIENT_ID_WEB = "Web_User"
PATH_TO_CERT = "certs/batt_sonnen-certificate.pem.crt"
PATH_TO_KEY = "certs/batt_sonnen-private.pem.key"
PATH_TO_ROOT = "certs/AmazonRootCA1.pem"
# TOPIC_PUBLISH = "gismolab-battery-sonnen"
TOPIC_PUBLISH_SONNEN = "gismolab/battery/66358/data"
TOPIC_PUBLISH_EGAUGE = "gismolab/monitoring/47571/data"
TOPIC_CONTROL = "gismolab-battery-sonnen"

# Sonnen info
# Add TOU endpoint and its configuration
# IP_farm = 'http://192.168.1.52' # sonnen_2 farm 67670 - without solar
# IP_farm = 'http://192.168.1.104' # sonnen_1 farm 67682 - with solar
IP_lab = 'http://198.129.119.220' # sonnen Gismo Lab
URL_BATT_INFO = IP_lab+":8080/api/battery"
URL_STATUS = IP_lab+":8080/api/v1/status"
URL_MANUAL_MODE = IP_lab+':8080/api/setting/?EM_OperatingMode=1' # (Change mode to manual mode)
URL_SELF_CONS = IP_lab+':8080/api/setting/?EM_OperatingMode=2' # (Change mode to self consumption mode)
URL_BACKUP = IP_lab+':8080/api/setting/?EM_OperatingMode=7' # (Change mode to backup mode)
URL_BATT_SETPOINT = IP_lab+':8080/api/v1/setpoint/'
HEADERS_SONNEN = {}
PAYLOAD_SONNEN = {}