#
# This file specifies the options for the flask run() commands
#
# See flask documentation for details
#

# Incoming request port
port = 5000

# Incoming connections address mask (use "0.0.0.0" to allow all incoming addresses)
host = "127.0.0.1" 

# Cache age limit
cache_expire = 60

# Enable HTTPS
ssl_context = None # 'adhoc' # None for HTTP only

# Enable CORS
enable_cors = True # Use True to enforce CORS check
