#include "inherit_perf_counter.h"

#include <cerrno>
#include <cstring>

#include "common.h"

/*
 * {@code InheritPerfCounter} constructor initializes performance counters
 * that are measured individually for a comlete execution. The constructor task
 * first parses the event name using libpfm, and identifies
 * the type of event (hardware, software, etc). It then calls perf_event_open
 * per counter.
 *
 * From: https://man7.org/linux/man-pages/man2/perf_event_open.2.html
 * struct read_format {
 *   u64 value;         The value of the event
 *   u64 time_enabled;  if PERF_FORMAT_TOTAL_TIME_ENABLED
 *   u64 time_running;  if PERF_FORMAT_TOTAL_TIME_RUNNING
 *   u64 id;            if PERF_FORMAT_ID
 *   u64 lost;          if PERF_FORMAT_LOST
 * };
 */
InheritPerfCounter::InheritPerfCounter(CounterData** counters,
                                       AgentState* agent_state)
    : counters(counters) {
  counter_debug("INHERITPERFCOUNTER: Initializing");
  for (uint i = 0; i < MAX_COUNTERS; i++) {
    fd[i] = -1;
  }
  num_counters = agent_state->get_num_events();
  /* Each counter has value, time enabled, time running, and ID. */
  size_counter_values = INHERIT_PERF_READ_VALUES * sizeof(counter_t);
  perf_event_attr_t pe_attr;
  pfm_perf_encode_arg_t pe_encode_arg;
  int ret;
  for (uint i = 0; i < num_counters; i++) {
    std::memset(&pe_attr, 0, sizeof(pe_attr));
    std::memset(&pe_encode_arg, 0, sizeof(pe_encode_arg));
    pe_encode_arg.size = sizeof(pe_encode_arg);
    pe_encode_arg.attr = &pe_attr;
    ret = pfm_get_os_event_encoding(agent_state->get_event(i).c_str(),
                                    PFM_PLM0 | PFM_PLM3, PFM_OS_PERF_EVENT_EXT,
                                    &pe_encode_arg);
    counter_assert(ret == PFM_SUCCESS, pfm_strerror(ret));
    pe_attr.size = sizeof(perf_event_attr);
    pe_attr.type = get_perf_event_type(agent_state->get_event(i));
    pe_attr.read_format = PERF_FORMAT_TOTAL_TIME_ENABLED |
                          PERF_FORMAT_TOTAL_TIME_RUNNING | PERF_FORMAT_ID;
    /* Counters are initally disabled */
    pe_attr.disabled = 1;
    pe_attr.inherit = 1;
    pe_attr.pinned = 1;
    fd[i] = perf_event_open(&pe_attr, 0, -1, -1, 0);
    counter_assert(fd[i] != -1, strerror(fd[i]));
    counters_start[i] = 0;
    counters_id[i] = 0;
  }
  current_phase = DISABLED_PHASE;
}

/*
 * This method reads the file descriptor with counter values, and does some
 * sanity checks.
 */
void InheritPerfCounter::read_counter(uint counter_idx) {
  counter_debug("INHERITPERFCOUNTER ({}): Reading counter", counter_idx);
  ssize_t ret =
      read(fd[counter_idx], &fd_counter_values, sizeof(fd_counter_values));
  counter_debug("INHERITPERFCOUNTER ({}): Finished reading counters",
                counter_idx);
  if (ret == -1) {
    counter_assert(ret != -1,
                   "INHERITPERFCOUNTER ({}): Failed to read value ({})",
                   counter_idx, strerror(errno));
  }
  counter_assert(ret == size_counter_values,
                 "INHERITPERFCOUNTER ({}): Incorrectly read value ({}, {})",
                 counter_idx, ret, size_counter_values);
  counter_assert(
      fd_counter_values[1] == fd_counter_values[2],
      "INHERITPERFCOUNTER ({}): Counter is being multiplexed ({} / {})",
      counter_idx, fd_counter_values[1], fd_counter_values[2]);
}

/*
 * This method enables the counters.
 */
void InheritPerfCounter::start(phase_t starting_phase) {
  counter_debug("INHERITPERFCOUNTER: Starting");
  for (uint i = 0; i < num_counters; i++) {
    ioctl(fd[i], PERF_EVENT_IOC_RESET, PERF_IOC_FLAG_GROUP);
    read_counter(i);
    counters_start[i] = fd_counter_values[0];
    counters_id[i] = fd_counter_values[3];
    ioctl(fd[i], PERF_EVENT_IOC_ENABLE, PERF_IOC_FLAG_GROUP);
  }
  current_phase = starting_phase;
}

/*
 * This method changes the phase of execution by reading the counters, and then
 * storing their value in the correct place.
 */
void InheritPerfCounter::change_phase(uint next_phase) {
  counter_debug("INHERITPERFCOUNTER: Changing phase: {}", next_phase);
  counter_assert(
      current_phase != DISABLED_PHASE,
      "INHERITPERFCOUNTER: Phase cannot be changed for stopped counter");
  counter_assert(current_phase != next_phase,
                 "INHERITPERFCOUNTER: Cannot change to current phase");
  for (uint i = 0; i < num_counters; i++) {
    read_counter(i);
    counters[i]->update_value(fd_counter_values[0] - counters_start[i],
                              current_phase);
    counters_start[i] = fd_counter_values[0];
    counter_assert(fd_counter_values[3] == counters_id[i],
                   "INHERITPERFCOUNTER ({}): Incorrect counter id", i);
  }
  current_phase = next_phase;
}

/*
 * This method stops/disables the counters.
 */
void InheritPerfCounter::stop() {
  counter_debug("INHERITPERFCOUNTER: Stopping");
  counter_assert(current_phase != DISABLED_PHASE,
                 "INHERITPERFCOUNTER: Counter must be started before stopping");
  change_phase(DISABLED_PHASE);
  for (uint i = 0; i < num_counters; i++) {
    ioctl(fd[i], PERF_EVENT_IOC_DISABLE, PERF_IOC_FLAG_GROUP);
    close(fd[i]);
  }
}
