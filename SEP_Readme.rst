
This prototype extends EPRI's OpenDER model to add interaction with a simple
DER Management System (DERMS) via a subset of the IEEE 2030.5 Smart Electric 
Profile standard.

Background
IEEE standards 1547 and 2030.5 define functionality and software interfaces
for smart 'grid-forming' inverters that can participate in maintaining grid
stability as needed to allow high penetration of renewable, carbon-free 
Distributed Energy Resources (DERs).  

Problem Statement
The electric power grid is a highly dynamic system wherein a variety of loads
with varying complex impedances come and go.  Power system engineers put a great
deal of effort into keeping Voltage, Frequency, and also the relationship 
between Reactive and Pure Resistive currents (aka the Power Factor) within
tight constraints. Renewable DERs such as wind and solar make this more 
challenging due to the variable and uncertain nature of their energy production
and because early generations of DC to AC inverters had limited ability to help
manage these parameters.  This puts additional burden on the central power
plants and other grid infrastructure, and limits the portion of energy the grid
can utilize from renewable DERs.

IEEE standard 1547 defines functionality for smart 'grid-forming' inverters 
that can help keep grid voltage, frequency, and power factor within required
limits thus enabling a higher penetration of renewable energy resources. 
IEEE standard 2030.5 further increases DER penetration by defining a web-based
SW interface to DER Management Systems (DERMS) that can have a global view of
the state of the grid and can orchestrate thousands of grid-forming DERs to
ultimately replace the central power plant as the dominant player in maintaining
grid stability.

Prototype
This simple prototype builds on the open source OpenDER software model created
by the Electric Power Research Institute (EPRI) which emulates an IEEE 
1547-compliant DER.  My prototype explores adding portions of the 2030.5
interface to monitor and  control the emulated DER.   The OpenDER model
is implemented in Python so the 2030.5 extensions in Python as well, which
may or may not be the best language for implementing the explicit data types,
sizes and layouts defined in 2030.5.  

The prototype implements some of the core functionality of 2030.5 including
the ability for a DERMS to discover a DER's capability, settings, and
operational status, and to control parameters such as reserved active power
headroom, and voltage and frequency ride-through and 'must trip' conditions.
The prototype helps show alignment between 1547 and 2030.5 functionality and
also where disconnects exist - such as the more extensive Must Trip, May Trip,
and Momentary Cessation curves required by 2030.5 which go beyond that required
by 1547.  

The prototype currently has many gaps from the extensive functionality defined
in 2030.5.  The most significant gap is that JSON is used for web data encoding
instead of the XML schema defined for 2030.5.  The software development
community has mostly moved to JSON today so Python has more current and 
better-supported JSON libraries, simplifying rapid prototyping.  The prototype
also skips over the Discovery and secure Authentication steps.  Finally,
since both sides of the prototype are implemented in Python, native Python
data types are used for many of the elements of 2030 data objects instead
of the elementary types defined in sep.xml.

V0.1 'alpha' Deltas from EPRI's OpenDER Model:
- Added a "Test DERMS" which runs as a separate process.
- Currently communicates with the OpenDER model through a local socket between
  the two processes.  Future goal is to move the Test DERMS to a uService on
  one of the major cloud platforms.
- Added top-level 'main_rt.py' that runs in real time in order to stay
  synchronized with the Test DERMS.
- Added basic 2030.5/SEP data object definitions and interface handler classes.
- At startup, 'discovers' the DERMS, reports nameplate and configuration
  parameters to the DERMS, then gets control parameters from the DERMS.
  During runtime, periodically reports status to the DERMS.
- Added a dictionary-based scheme to facilitate simulating more variations
  in Voltage and Frequency at the PCC.

Git branch 'multiDER' deltas:
- Adds support for multiple DERs all interacting with one DERMS 2030.5 server;
- Adds src/opender/Parameters/Event-list.csv, a .csv spreadsheet containing 
  Frequency and Voltage change events for each DER;
- Adds the C shell script md_sim.csh to to run multiple DER instances.

Additional Python Package Dependencies which may require a pip install:
- time
- pause
- logging
- requests
- json
- http
- socketserver

Running the Model
Using Python3, first start 'test_derms.py <m>' in one Linux or OS X
shell/process where 'm' is the max number of DERs supported.  This will 
listen on localhost port 8000.  Then, in a separate shell execute
'md_sim.csh <n>' where n <= m is the number of DER instances. 
sep_client.py is currently hard-coded with a DERMS address on the local
machine but can easily be modified to reference the Test DERMS running on a
separate server on the same LAN.  Either way, 'main_rt.py' will 'discover'
the test DERMS and then execute the enhanced OpenDER model in real time.

Optionally edit src/opender/Parameters/Event-list.csv to add points in time
where either Volts pu or Frequency at the reference point for a specific DER
instance.  Leave all other cells blank in the .csv file.


