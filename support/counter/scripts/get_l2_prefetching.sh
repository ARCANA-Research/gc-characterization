#!/bin/bash

MSR_REG=0x1A4
CPUID=0
CPUCOUNT=47
while [ $CPUID -le $CPUCOUNT ]
do
    rdmsr -p $CPUID $MSR_REG
    CPUID=$((CPUID + 1))
done
exit 0
