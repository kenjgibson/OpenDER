#!/bin/csh
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
#
# This script starts a multiple DER simulation using OpenDER. 
# First start the Test DERMS either in a separate shell/process
# or on a separate server with address as defined in sep_client.py.
# Start the DERMS with the command:
#     ./test_derms.py <m>
# where <m> is the max number of DERs supported
#
# Then invoke this script to start the OpenDER instances with the command:
#     ./md_sim.csh <n>
# where n <= m is the number of DERs to simulate.
# The script assumes the Python executables are in the current directory.
#
# The DER processes will exit once they complete their time steps.
# Press Ctrl-C to stop the Test DERMS process.

# Function to handle cleanup on Control-C
onintr cleanup

# Check if the correct number of arguments is provided
if ($#argv != 1) then
    echo "Usage: $0 <Num DERs>"
    exit 1
endif

# Get the DER count from the command line argument
set der_count = $1

# Start each OpenDER instance as background tasks
@ i = 0
while ($i < $der_count)
    ./main_rt.py $i &
    @ i++
end

# Wait for DER processes to finish
wait

cleanup:
    exit 1
end



