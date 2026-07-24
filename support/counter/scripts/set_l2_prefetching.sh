#!/bin/bash

MSR_VAL=0
MSR_REG=0x1A4
CPUID=0
CPUCOUNT=47
while [ $CPUID -le $CPUCOUNT ]
do
    wrmsr -p $CPUID $MSR_REG $MSR_VAL
    CPUID=$((CPUID + 1))
done
CPUID=0
while [ $CPUID -le $CPUCOUNT ]
do
    if [ $(rdmsr -p $CPUID $MSR_REG) != $MSR_VAL ]; then
        echo "ERROR setting $CPUID"
        exit 1
    fi
    CPUID=$((CPUID + 1))
done
echo "SUCCESS"
exit 0
