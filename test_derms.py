#!/usr/bin/env Python3
#
# Copyright 2024 Kenneth J. Gibson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" Simple IEEE 2030.5 Smart Energy Profile protocol server.

Simple prototpe of a Distributed Energy Resource Management Server (DERMS)
using portions of the IEEE 2030.5 Smart Energy Profile protocol.
  
Following IEEE 2030.5, the DERMS acts as an HTTP server and DERs as clients.
DERs discover and register with the DERMS and provide Nameplate,
Configuration, and Status information through HTTP PUT and POST messages.
They retreive commands and control actions through GETs.

2030.5 requires content type "application/sep+xml", or "application/sep-exi"
but for now, I am using JSON as today's popular standard for exchanging
data through HTTP.  Also because right now I can't find a Python XML parser
that can parse the 2030.5 SEP XML files.
 
This simple prototpe supports just one DER and Polling only (no subscription
support).  Also, discovery and security are not yes supported.
  
"""

__authors__ = [
  '"Ken Gibson" <kenjgibson@gmail.com>'
]

import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
import socketserver
import time
import json
import logging
from sep_types import *

logging.basicConfig(level=logging.INFO)

max_ders = 100       #Some reasonable number.  Can be changed

# Accept the number of DERs as a param.  This emulates the 2030.5 usage
# wherein DERs are registered out-of-band prior to online discovery so
# the DERMS knows how many DERs it is managing before they connect online
if len(sys.argv) < 2:
    # No parameter supplied. Assume single-DER simulation
    num_ders = 1
else:
    try:
        num_ders = int(sys.argv[1])
    except ValueError:  
        print(f"Usage: EndpointTest.py <integer> n range 1..{max_ders}")
        sys.exit(1)
if num_ders > max_ders:
    print(f"Max number of DERs supported is {max_ders}")
    sys.exit(1)
else:
    logging.info(f"Starting DERMS with max {num_ders} DERs")

# Set port for local socket between two local processes
PORT = 8000
ENCODING = "utf-8"
hostName = "localHost"
contentType = "application/json"

# Set a fast pollRate to speed up the simulation
pollRate = 3        # seconds

# lists with 2030.5 objects for each DER
derCapList=[]
derSettingsList=[]
derStatusList =[]
derCtlBaseList =[]
ddrcList=[]

# Create a 2030.5 Device Capability object for each DER to 'GET'
# There is only one of these.

devCap = DeviceCapability()
devCap.set('pollRate', pollRate)
devCap.set('flags', DC_pollRate_exists)

# Allocate Capability, Settings, and Status objects for each DER.
# Any real DERMS app will need to manage thousands of DERs so would likely
# organize these into a modern cloud database.
for der in range(0,num_ders):
    derCapList.append(DERCapability())
    derSettingsList.append(DERSettings())
    derStatusList.append(DERStatus())

# Create a DERControlBase objects with default parameters for the DER
# First create the default curves for under and over Voltage and Freq.
# IEEE 2030 requires that DERs support a minimum of 10 curve points
# for each of Momentary Cessation, May Trip and Must Trip for V and Freq.
# HOWEVER, the OpenDER model only meets the IEEE 1547 requirement for
# two points and only for Must Trip AND those points must be within
# a more limited range than 2030.
# For now, provide those simplified Must Trip curves as well as
# some May Trip and Momentary Cessation examples that will be ignored by
# the OpenDER model.
# Shortcut for now: use native Python Tuple and List types
# Note: Time values are in 100ths of Seconds.  I can't find this in the spec
# but since fractional seconds must be supported and the y value is an Int32,
# the units must be something similar.
defLVMustTripCurve = [(16,50),(200,80)]         # Complies with 1547
defLVMCCurve = [(0,70), (150, 70)]
defLVMayTripCurve = [(100,0), (100,80), (1000,80), (1000,90), (2000,88), (10000,88)]
defHVMustTripCurve = [(16,120), (110,110)]      # Complies with 1547
defHVMCCurve = [(0,110), (1300,110)]
defHVMayTripCurve = [(16,130), (16,120), (1200,120), (1200,110), (10000,110)]
# Note, for frequency, y value switches from %nominal to actual Hz value
defLFMustTripCurve = [(16,57), (20000,59)]      # Complies with 1547
defLFMayTripCurve = [(0,58), (30000,58)]
defHFMustTripCurve = [(16,62), (20000,61)]      # Complies with 1547
defHFMayTripCurve = [(0,62), (30000,62), (30000,61), (10000,61)]

# Allocate the control objects for each DER. 
# Give each DER the same settings for now.  More advanced simulations
# may want to vary the settings
for der in range(0,num_ders):
    derCtlBaseList.append(DERControlBase())
    # Set the curves
    derCtlBaseList[der].set('opModHFRTMustTrip', defHFMustTripCurve)
    derCtlBaseList[der].set('opModHVRTMomentaryCessation', defHVMCCurve)
    derCtlBaseList[der].set('opModHVRTMustTrip', defHVMustTripCurve)
    derCtlBaseList[der].set('opModLFRTMustTrip', defLFMustTripCurve)
    derCtlBaseList[der].set('opModLVRTMomentaryCessation', defLVMCCurve)
    derCtlBaseList[der].set('opModLVRTMustTrip', defLVMustTripCurve)
    # Set scalar values
    derCtlBaseList[der].set('opModConnect', 'ENABLED')   # DER is connected
    derCtlBaseList[der].set('opModEnergize', 'ENABLED')  # Is energized
    derCtlBaseList[der].set('opModFixedPF', 'ENABLED')   # Default in OpenDER model
    derCtlBaseList[der].set('opModFixedVar', 'ENABLED')  # 1 == %setMaxW
    derCtlBaseList[der].set('opModFixedW', 100)          # 100% for now
    derCtlBaseList[der].set('opModFreqDroop', 100)       # 100% for now
    derCtlBaseList[der].set('opModMaxLimW', 90)          # 90% to see what the model does
    derCtlBaseList[der].set('opModTargetVar', 'DISABLED')   
    derCtlBaseList[der].set('opModTargetW', 'DISABLED')
    derCtlBaseList[der].set('rampTms', 500)          #100ths of S to transition modes

    # Set the default DER Control which contains a link to the derCtlBase
    # Again, focus on the required fields as defined in 2030.5 annex E.  
    # The DER will issue a GET to retrieve this.
    ddrcList.append(DefaultDERControl())
    # All of the following types should be UInt16 per 2030.5
    # In general, set to OpenDER model defaults for now
    ddrcList[der].set('setESDelay', 200)         # 2 Seconds, faster than 1547 default
    ddrcList[der].set('setESHighFreq', 6010)     # 60.1 Hz, 1547 default 
    ddrcList[der].set('setESHighVolt', 105)      # 105% of nominal, 1547 default
    ddrcList[der].set('setESLowFreq', 5950)      # 59.5 Hz, 1547 default
    # Spec Question:  2030 says this field is a UInt16 containing 100ths of %
    # BUT, the 1547 default is 91.7% which which requires either a Float type
    # or units to be 1,000th of %
    ddrcList[der].set('setESLowVolt', 92)        # 1547 says 91.7% of nominal
    # Model requires either Random delay or Ramp rate (GradW) to be 0
    ddrcList[der].set('setESRandomDelay', 0)     
    ddrcList[der].set('setGradW', 300)           # 3S ramp rate, 1547 default
    # The Python JSON library can't serialize the DER Control Base object
    # so store its dictionary
    ddrcList[der].set('DERControlBase', derCtlBaseList[der].toDict())  

# Add handler class as subclass of http.server.BaseHTTPRequestHandler
# will be passed to the http daemon with member functions to handle 
# Get, Post, Head etc.
class sepHandler( BaseHTTPRequestHandler ):
    # Overide the GET handler to respond with control and other info as
    # specified in 2030.5.  In this prototype, deviate from 2030.5 and 
    # serialize into JSON instead of XML.
    # The fields from the GET request are stored in member instance vars
    # before this is invoked.
    # NOTE:  json.dump() encodes into json.  Load() decodes
    def do_GET(self):
        logging.debug( f"GET path = {self.path}")
        pathElements = self.path.split("/")
        # Element 0 is the leading '/'
        if pathElements[1] == 'tm':
            rspStatus = 200         # HTTP general success
            rspBody = json.dumps(time.time())
            logging.debug( "Returning time")
        elif pathElements[1] == 'dcap':
            rspStatus = 200
            dict = devCap.toDict()
            rspBody = json.dumps(dict)
            logging.debug( "Returning Device Capability")
        elif pathElements[1] == 'derp':
            # Get the DER ID
            try:
                der_num = int(pathElements[2])
            except ValueError:
                logging.error(f"Bad DER ID in path: {self.path}")
                self.send_response(404)             # Not implementd
                self.end_headers()                  # send this response
                return   
            if der_num < 0 or der_num >= num_ders:
                logging.error(f"DER ID out of range: {der_num}")
                self.send_response(404)             # Not implementd
                self.end_headers()
                return
        
            if pathElements[3] == 'dderc':              # Default DER Control
                # Serialize the Default DER Control which contains a DER
                # Control Base, which contains default curve lists
                dict = ddrcList[der_num].toDict()
                rspBody = json.dumps(dict)
                rspStatus = 200
            elif pathElements[3] == 'derc':           # DER Control
                logging.debug( "GET for DER Ctl received.  Not implemented yet")
                rspStatus = 404
                rspBody = None
            else:
                logging.warning( f"GET to unknown path: {self.path}")
                rspStatus = 404         # Resource not valid or not implementd
                rspBody = None

        # Build up the response header fields in an internal buffer that will
        # be sent when self.end_headers() is invoked.
        self.send_response(rspStatus)
        self.send_header("Content-type", contentType)     
        self.end_headers()              #causes the action to send
        # write the response body to the output stream following HTTP protocol
        if rspBody is not None:
            self.wfile.write(bytes(rspBody, ENCODING))
        else:
            self.wfile.write(bytes("Resource not valid or not implemented yet", ENCODING))

    # Add a POST handler.
    # Not extensively used in 2030.5.  The Response List object is one object
    # provided to the DERMS via a POST.
    # The fields from the POST request are stored in member instance vars
    # This handler expects a JSON string in the body of the POST request.
    # The JSON string is parsed into a Python dictionary.
    # An error response is sent if the JSON string is not valid or if content type
    # is something other than "application/json".
    def do_POST(self):
        if self.headers['Content-Type'] != contentType:
            logging.warning(f"POST received unsupported media type {self.headers['Content-Type']}")
            self.send_response(415)         #HTTP unsupported media type
        else:
            logging.debug( f"JSON content received: {self.rfile.read(int(self.headers['Content-Length']))}" )
            self.send_response(200)         #HTTP general success
        self.end_headers()                  #causes the action to send
        
    # Add PUT handler.
    # Most data communicated from the DERs to the DERMS is via http PUT verbs
    # In a real implementation, each DER would have its own endpoint path based
    # on its device ID.  This simple prototype only supports one DER so the
    # device IDs are removed in the paths.
    def do_PUT(self):
        if self.headers['Content-Type'] != contentType:
            self.send_response(415)         #HTTP unsupported media type
            self.end_headers()              #send this response
            return

        pathElements = self.path.split("/")
        # Element 0 is the leading '/'
        # For now, everything handled by PUT is under /edev
        if pathElements[1] != "edev":
            logging.error(f"PUT to unhandled path: {self.path}")
            self.send_response(404)             # Not implementd
            self.end_headers()                  #send this response
            return

        # Get the DER number from the path
        try:
            der_num = int(pathElements[2])
        except ValueError:
            logging.error(f"Bad DER ID in path: {self.path}")
            self.send_response(404)             # Not implementd
            self.end_headers()                  # send this response
            return

        if der_num < 0 or der_num >= num_ders:
            logging.error(f"DER ID out of range: {der_num}")
            self.send_response(404)             # Not implementd
            self.end_headers()
            return

        if pathElements[3] == "cfg":
            # The DER is sending its confiiguration info.
            # Not saving in this prototype but return success.
            self.send_response(200)
            self.end_headers()
            return

        if pathElements[3] != "der":
            logging.error(f"PUT to unknown path: {self.path}")
            self.send_response(404)             # Not implementd
            self.end_headers()
            return

        match pathElements[4]:
            case 'dercap':        # DER Capability
                # Get the body and decode into dictionary
                body = self.rfile.read(int(self.headers['Content-Length']))
                dict = json.loads(body)
                logging.debug(f"DER Capability dictionary received: {dict}")
                self._handle_DERCap(der_num, dict)
                rspStatus = 200
                rspBody = None
            case 'derg':          # DER Settings
                body = self.rfile.read(int(self.headers['Content-Length']))
                dict = json.loads(body)
                logging.debug(f"DER settings dictionary received: {dict}")
                self._handle_DERSettings(der_num, dict)
                rspStatus = 200
                rspBody = None
            case 'ders':             # DER Status
                body = self.rfile.read(int(self.headers['Content-Length']))
                dict = json.loads(body)
                logging.debug(f"DER Status dictionary received: {dict}")
                self._handle_DERStatus(der_num, dict)
                rspStatus = 200
                rspBody = None
            case 'dera':          # DER Availability
                logging.warning("PUT DER Availability.  Not implemented yet")
                rspStatus = 404
                rspBody = None
            case _:                # Anything else not supported
                logging.error(f"PUT to unknown path: {self.path}")
                rspStatus = 404
                rspBody = None
                
        self.send_response(rspStatus)
        self.end_headers()              #causes the action to send

    # Private methods to accept objects from the DER as a dictionary
    # Again, in this simple test program, supports only one DER.  A real
    # implementation would accespt a Device ID and likely organize the capability
    # objects into a database
    def _handle_DERCap(self, der, dict):
        derCapList[der].fromDict(dict)

    def _handle_DERSettings(self, der, dict):
        derSettingsList[der].fromDict(dict)

    def _handle_DERStatus(self, der, dict):
        derStatusList[der].fromDict(dict)

# if running as a standalone daemon vs. imported, start the server
if __name__ == "__main__":        
    with HTTPServer((hostName, PORT), sepHandler) as webServer:
        logging.info(f"2030.5 server started on port: {PORT}")
        try:
            webServer.serve_forever()
        except KeyboardInterrupt:
            pass
        webServer.server_close()

    logging.info("Server stopped.") 


