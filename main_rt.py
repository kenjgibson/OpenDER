#!/usr/bin/env Python3
# Copyright © 2023 Electric Power Research Institute, Inc. All rights reserved.
# Copyright © 2023 Kenneth J Gibson   kenjgibson@gmail.com

# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met: 
# · Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# · Redistributions in binary form must reproduce the above copyright notice, 
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# · Neither the name of the EPRI nor the names of its contributors may be used 
#   to endorse or promote products derived from this software without specific
#   prior written permission.

# -*- coding: utf-8 -*-

import pathlib
import os
import matplotlib.pyplot as plt
import opender as der
#   Additions for real-time simulation
import time
import pause
#   Add IEEE 2030.5 Smart Energy Profile (SEP) interface
from    sep_types import *
import  sep_client as sep

# Define DER parameter configuration directory (optional)
script_path = pathlib.Path(os.path.dirname(__file__))
as_file_path = script_path.joinpath("src", "opender", "Parameters", "AS-with std-values.csv")
model_file_path = script_path.joinpath("src", "opender","Parameters", "Model-parameters.csv")
file_ss_obj = der.common_file_format.DERCommonFileFormat(as_file_path, model_file_path)

# creating DER
der_test = der.DER(file_ss_obj)

# assign simulation time step in Seconds
t_s = 1
der.DER.t_s = t_s
t = 0

# prepare arrays for plotting
t_plot = []
v_plot = []
pdc_plot = []
p_plot = []
q_plot = []
stat_plot = []
debug_plot = []

der_test.der_file.QV_MODE_ENABLE = True
der_test.der_file.NP_ABNORMAL_OP_CAT = 'Cat_II'

# Create a SEP Client to handle the 2030.5 interface with the DERMS
sep_handler = sep.SEPClient()
# Discover and authenticate with the DERMS
sep_handler.discoverDERMS()

# Get the 2030.5 Device Capability from the DERMS
dev_cap = sep_handler.getDevCap()
poll_rate = dev_cap.get('pollRate')

# Initialize a 2030.5 DER Capability object for reporting this model's
# Nameplate capabilities to the DERMS.  2030.5 defines language-agnostic
# floating point objects for various parameters.  For this prototype, both
# endpoints are implemented in Python so just using python Float type.

der_cap = DERCapability()
# Report the Control Modes supported.
# 2030.5 and 1547 use different terminology.  Attempting to correlate the two
# with the help of 2030.5 Annex E.
mode_flags = capOpModFixedPFInjectW | capOpModFixedVar           \
        | capOpModFixedW | capOpModFreqDroop | capOpModFreqWatt
der_cap.set('modesSupported', mode_flags)
# Initialize various Nameplate ratings
# NOTE: May need to translate Abnormal Op Cat to 2030 value
der_cap.set('rtgAbnormalCategory', der_test.der_file.NP_ABNORMAL_OP_CAT)
der_cap.set('rtgAh', float(der_test.der_file.NP_P_MAX_CHARGE))
# Skip Minimum Negative Pwr Factor.  Not required per 2030.5 Annex E
# and I can't find it in the OpenDER model.
der_cap.set('rtgNormalCategory', der_test.der_file.NP_NORMAL_OP_CAT)
der_cap.set('rtgOverExcitedPF', float(der_test.der_file.NP_OVER_PF))
der_cap.set('rtgOverExcitedW', float(der_test.der_file.NP_P_MAX_OVER_PF))
der_cap.set('rtgUnderExcitedPF', float(der_test.der_file.NP_UNDER_PF))
der_cap.set('rtgUnderExcitedW', float(der_test.der_file.NP_P_MAX_UNDER_PF))
der_cap.set('rtgVA', float(der_test.der_file.NP_VA_MAX))
der_cap.set('rtgVar', float(der_test.der_file.NP_Q_MAX_INJ))
der_cap.set('rtgVarNeg', float(der_test.der_file.NP_Q_MAX_ABS))
der_cap.set('rtgW', float(der_test.der_file.NP_P_MAX))
der_cap.set('rtgWh', float(der_test.der_file.NP_P_MAX_CHARGE))
der_cap.set('DERtype', TYPE_PV)

# ifdef DEBUG
theDict = der_cap.toDict()
for key in theDict.keys():
    print("For key ", key, "type is ", type(theDict[key]))
# endif

# 'PUT' the DER Capability to the DERMS
sep_handler.sendDERCap(der_cap)

# Report required DER Settings.  These are similar to NP values for the DER
# but as described in 2030.5, are configurable settings when installing the DER
# or changed only rarely during maintenance.
# Many fields in this object are duplicates of the NP values in the 
# DER Capabilities.  If the DER's settings do not deviate from NP, then fields
# can be left blank.
# Model variables are in units of Volts, HZ, %.  2030.5 units are hundredths
# For now, initialize the mandatory fields as required in 2030.5 Annex E
# NOTE To-do:  Most of these fields should be UInt16
der_settings = DERSettings()
der_settings.set('setESDelay', float(der_test.der_file.ES_DELAY*100))
der_settings.set('setESHighFreq', float(der_test.der_file.ES_F_HIGH*100))
der_settings.set('setESHighVolt', float(der_test.der_file.ES_V_HIGH*100))
der_settings.set('setESLowFreq', float(der_test.der_file.ES_F_LOW*100))
der_settings.set('setESLowVolt', float(der_test.der_file.ES_F_HIGH*100))
der_settings.set('setESRandomDelay',                    \
            float(der_test.der_file.ES_RANDOMIZED_DELAY*100))  # in .01 Secs
der_settings.set('setGradW', float(der_test.der_file.ES_RAMP_RATE*100))
der_settings.set('setVRef', float(der_test.der_file.NP_AC_V_NOM))    # in Volts
der_settings.set('setVRefOfs', float(0))    #Assume inverter connected to PCC
sep_handler.sendDERSettings(der_settings)

#Get the Default DER Control Parameters for the DER
dderc = sep_handler.getDDERC()
# Convert the DER Control Base from a serializable dictionary back to an object
base = DERControlBase()
base.fromDict(dderc.get('DERControlBase'))
dderc.set('DERControlBase', base)
# ifdef DEBUG
theDict = dderc.get('DERControlBase').toDict()
print("The Control Base fields:")
for key in theDict.keys():
    print("For key ", key, "value is ", theDict[key])
# endif

# IEEE 2030 says DERs must support a minimum of 10 curve points however it 
# appears the current OpenDER model supports only two and only for V and freq
# Must Trip (no Momentary Cessation or May Trip).  Set those values based
# on the first two curve points.
# The 2030.5 curves are in time-order where the larger deviations typically
# trip sooner.  In 1547, the trip variables go in the opposite order
ctlBase = dderc.get('DERControlBase')
der_test.der_file.OV1_TRIP_V = ctlBase.get('opModHVRTMustTrip')[1][1]/100
der_test.der_file.OV1_TRIP_T = ctlBase.get('opModHVRTMustTrip')[1][0]/100
der_test.der_file.OV2_TRIP_V = ctlBase.get('opModHVRTMustTrip')[0][1]/100
der_test.der_file.OV2_TRIP_T = ctlBase.get('opModHVRTMustTrip')[0][0]/100

der_test.der_file.UV1_TRIP_V = ctlBase.get('opModLVRTMustTrip')[1][1]/100
der_test.der_file.UV1_TRIP_T = ctlBase.get('opModLVRTMustTrip')[1][0]/100
der_test.der_file.UV2_TRIP_V = ctlBase.get('opModLVRTMustTrip')[0][1]/100
der_test.der_file.UV2_TRIP_T = ctlBase.get('opModLVRTMustTrip')[0][0]/100

der_test.der_file.OF1_TRIP_F = ctlBase.get('opModHFRTMustTrip')[1][1]
der_test.der_file.OF1_TRIP_T = ctlBase.get('opModHFRTMustTrip')[1][0]/100
der_test.der_file.OF2_TRIP_F = ctlBase.get('opModHFRTMustTrip')[0][1]
der_test.der_file.OF2_TRIP_T = ctlBase.get('opModHFRTMustTrip')[0][0]/100

der_test.der_file.UF1_TRIP_F = ctlBase.get('opModLFRTMustTrip')[1][1]
der_test.der_file.UF1_TRIP_T = ctlBase.get('opModLFRTMustTrip')[1][0]/100
der_test.der_file.UF2_TRIP_F = ctlBase.get('opModLFRTMustTrip')[0][1]
der_test.der_file.UF2_TRIP_T = ctlBase.get('opModLFRTMustTrip')[0][0]/100

der_test.der_file.CONST_PF_MODE_ENABLE = ctlBase.get('opModFixedPF')
der_test.der_file.CONST_Q_MODE_ENABLE = ctlBase.get('opModFixedVar')
der_test.der_file.NP_MODE_TRANSITION_TIME = ctlBase.get('rampTms')/100

der_test.der_file.ES_DELAY = dderc.get('setESDelay') # Both units are .01 S
der_test.der_file.ES_F_HIGH = dderc.get('setESHighFreq')/100
der_test.der_file.ES_V_HIGH = dderc.get('setESHighVolt')/100
der_test.der_file.ES_F_LOW = dderc.get('setESLowFreq')/100
der_test.der_file.ES_V_LOW = dderc.get('setESLowVolt')/100
der_test.der_file.ES_RANDOMIZED_DELAY = dderc.get('setESRandomDelay')
der_test.der_file.ES_RAMP_RATE = dderc.get('setGradW')

der_test.update_der_input(f=60, p_dc_pu=1)
# For real-time simulation
start_time = time.time()    #Seconds since epoch    
while t < 2400:
    if (t < 5)or(100<t<800)or(900<t<1600)or(1700<t<2400):
        der_test.update_der_input(v_pu=1)
    else:
        der_test.update_der_input(v_pu=1.11)

    # Show the simulation is still alive in real-time simulation
    if t%5 == 0:
        print("Time step = ", t)

    # calculate output power at each time step
    der_test.run()

    # save result
    t_plot.append(t)
    p_plot.append(der_test.p_out_pu)
    q_plot.append(der_test.q_out_pu)
    pdc_plot.append(der_test.der_input.p_avl_pu)
    v_plot.append(der_test.der_input.v_meas_pu)
    stat_plot.append(der_test.der_status)

    # increase t
    t = t + t_s
    # For real-time simulation, pause until the correct time for the next iteration
    try:
        pause.until(t*t_s + start_time)
    except KeyboardInterrupt:
        print("Keyboard interrupt.  Ending simulation.")
        break

# plot
fig = plt.figure(figsize=[15,10])
plt.clf()
ax1=plt.subplot(4, 1, 1)
plt.plot(t_plot, v_plot, label = 'Voltage (pu)')
plt.grid()
plt.legend()
plt.subplot(4, 1, 2, sharex=ax1)
plt.plot(t_plot, pdc_plot, label='P_dc (pu)')
plt.plot(t_plot, p_plot, label='P_out (pu)')
plt.grid()
plt.legend()
plt.subplot(4, 1, 3, sharex=ax1)
plt.plot(t_plot, q_plot, label='Q_out (pu)')
plt.grid()
plt.legend()
plt.subplot(4, 1, 4, sharex=ax1)
plt.plot(t_plot, stat_plot, label='der status')
plt.grid()
plt.legend()
plt.xlabel('Time (s)')
plt.show()