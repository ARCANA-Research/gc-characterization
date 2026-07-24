#!/bin/bash

VALUE="performance"
CPUID=0
CPUCOUNT=47

while [ $CPUID -le $CPUCOUNT ]
do
    echo $VALUE > /sys/devices/system/cpu/cpu$CPUID/cpufreq/scaling_governor
    CPUID=$((CPUID + 1))
done
CPUID=0
while [ $CPUID -le $CPUCOUNT ]
do
    if [ $(cat /sys/devices/system/cpu/cpu$CPUID/cpufreq/scaling_governor) != $VALUE ]; then
        echo "ERROR setting $CPUID"
        exit 1
    fi
    CPUID=$((CPUID + 1))
done
echo "SUCCESS"
exit 0