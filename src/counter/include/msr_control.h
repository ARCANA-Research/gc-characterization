#ifndef MSR_CONTROL_H
#define MSR_CONTROL_H

#include <cstdint>

#include "base.h"

#define MSR_NUM_CPUS 24

/* MSR_PREFETCH_CONTROL -> 0x1A4 */
#define PREFETCH_MSR 0x1A4

/* ============================= HELPER METHODS ============================= */

std::string get_msr_path(uint cpu);
uint64_t get_msr_value(uint cpu, uint64_t msr_reg);
void set_msr_value(uint cpu, uint64_t msr_reg, uint64_t new_value);
void enable_prefetcher(uint cpu);
void disable_prefetcher(uint cpu);

#endif  // MSR_CONTROL_H
