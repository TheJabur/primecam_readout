#!/bin/bash
killall ptp4l
ptp4l -i eth0 -f gPTP.cfg --step_threshold=1 & 
