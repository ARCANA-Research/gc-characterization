/*
 * Controls MSR registers.
 * Based on Intel's msr-tools program: https://github.com/intel/msr-tools
 */

#include "msr_control.h"

#include <fcntl.h>
#include <unistd.h>

#include "common.h"

/* =============================== MSR CONTROL ============================== */

std::string get_msr_path(uint cpu) {
  return "/dev/cpu/" + std::to_string(cpu) + "/msr";
}

uint64_t get_msr_value(uint cpu, uint64_t msr_reg) {
  int msr_fd = open(get_msr_path(cpu).c_str(), O_RDONLY);
  if (msr_fd == -1) {
    counter_assert(msr_fd != -1, "PREFETCHERERROR: Could not open fd ({})",
                   strerror(errno));
  }
  uint64_t msr_data;
  ssize_t msr_ret = pread(msr_fd, &msr_data, sizeof(msr_data), msr_reg);
  if (msr_ret < 0) {
    counter_assert(msr_ret != -1,
                   "PREFETCHERERROR: Could not read register ({})",
                   strerror(errno));
  }
  counter_assert(msr_ret == sizeof(msr_data),
                 "PREFETCHERERROR: Incorrectly read size ({} != {})", msr_ret,
                 sizeof(msr_data));
  counter_warn("PREFETCH: Get MSR {} for CPU {} -> {}", msr_reg, cpu, msr_data);
  return msr_data;
}

void set_msr_value(uint cpu, uint64_t msr_reg, uint64_t new_value) {
  int msr_fd = open(get_msr_path(cpu).c_str(), O_WRONLY);
  if (msr_fd < 0) {
    counter_assert(msr_fd != -1, "PREFETCHERERROR: Could not open fd ({})",
                   strerror(errno));
  }
  ssize_t msr_ret = pwrite(msr_fd, &new_value, sizeof(new_value), msr_reg);
  if (msr_ret == -1) {
    counter_assert(msr_ret != -1,
                   "PREFETCHERERROR: Could not read register ({})",
                   strerror(errno));
  }
  counter_assert(msr_ret == sizeof(new_value),
                 "PREFETCHERERROR: Incorrectly read size ({} != {})", msr_ret,
                 sizeof(new_value));
  counter_warn("PREFETCH: Set MSR {} for CPU {} -> {}", msr_reg, cpu,
               new_value);
  uint64_t curr_value = get_msr_value(cpu, msr_reg);
  counter_assert(curr_value == new_value,
                 "PREFETCHERROR: Could not set value correctly {} != {}",
                 curr_value, new_value);
}

void enable_prefetcher(uint cpu) {
  int64_t curr_value = get_msr_value(cpu, PREFETCH_MSR);
  set_msr_value(cpu, PREFETCH_MSR, 0);
  counter_warn("PREFETCH: ENABLE (CPU {} CURR {} NEW {})", cpu, curr_value, 0);
}

void disable_prefetcher(uint cpu) {
  int64_t curr_value = get_msr_value(cpu, PREFETCH_MSR);
  set_msr_value(cpu, PREFETCH_MSR, 0b11);
  counter_warn("PREFETCH: DISABLE (CPU {} CURR {} NEW {})", cpu, curr_value,
               0b11);
}
