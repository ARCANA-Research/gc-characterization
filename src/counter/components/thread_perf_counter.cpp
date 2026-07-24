#include "thread_perf_counter.h"

#include <cerrno>
#include <cstring>

#include "common.h"

/*
 * {@code ThreadPerfCounter} constructor initializes a group of performance
 * counters for a thread, that are NOT inherited, and are measured together to
 * improve accuracy and speed. The constructor task first parses the event name
 * using libpfm, and identifies the type of event (hardware, software, etc).
 * Then the first event starts a group of counters (fd = -1), and the remaining
 * events use the fd of the first counter.
 *
 * From: https://man7.org/linux/man-pages/man2/perf_event_open.2.html
 * struct read_format {
 *   u64 nr;            The number of events
 *   u64 time_enabled;  if PERF_FORMAT_TOTAL_TIME_ENABLED
 *   u64 time_running;  if PERF_FORMAT_TOTAL_TIME_RUNNING
 *   struct {
 *       u64 value;     The value of the event
 *       u64 id;        if PERF_FORMAT_ID
 *       u64 lost;      PERF_FORMAT_LOST
 *   } values[nr];
 * };
 */
ThreadPerfCounter::ThreadPerfCounter(tid_t tid, CounterData** counters,
                                     AgentState* agent_state)
    : counters(counters), tid(tid) {
  counter_debug("THREADPERFCOUNTER ({}): Initializing", tid);
  counter_assert(tid != 0, "THREADPERFCOUNTER ({}): Initializing");
  perf_event_attr_t pe_attr;
  pfm_perf_encode_arg_t pe_encode_arg;
  int ret;
  num_counters = agent_state->get_num_events();
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
                          PERF_FORMAT_TOTAL_TIME_RUNNING | PERF_FORMAT_ID |
                          PERF_FORMAT_GROUP;
    /* Counters are initally disabled */
    pe_attr.disabled = 1;
    pe_attr.inherit = 0;
    if (i == 0) {
      /* Counters should not be multiplexed, and this attribute is for leader */
      pe_attr.pinned = 1;
      fd = perf_event_open(&pe_attr, tid, -1, -1, 0);
      counter_assert(fd != -1, strerror(fd));
    } else {
      ret = perf_event_open(&pe_attr, tid, -1, fd, 0);
      counter_assert(ret != -1, strerror(ret));
    }

    counters_start[i] = 0;
    counters_id[i] = 0;
  }
  /* Each counter has group, and the first three values are for time running. */
  num_counter_values = 3 + (2 * num_counters);
  size_counter_values = num_counter_values * sizeof(counter_t);
  current_phase = DISABLED_PHASE;
}

/*
 * This method reads the file descriptor with counter values, and does some
 * sanity checks.
 */
void ThreadPerfCounter::read_counters() {
  counter_debug("THREADPERFCOUNTER ({}): Reading counters", tid);
  ssize_t ret = read(fd, &fd_counter_values, sizeof(fd_counter_values));
  counter_debug("THREADPERFCOUNTER ({}): Finished reading counters", tid);
  if (ret == -1) {
    counter_assert(ret != -1,
                   "THREADPERFCOUNTER ({}): Failed to read value ({})", tid,
                   strerror(errno));
  }
  counter_assert(ret == size_counter_values,
                 "THREADPERFCOUNTER ({}): Incorrectly read value ({}, {})", tid,
                 ret, size_counter_values);
  counter_assert(
      fd_counter_values[0] == num_counters,
      "THREADPERFCOUNTER ({}): Incorrect number of counters read in perf group",
      tid);
  counter_assert(fd_counter_values[1] == fd_counter_values[2],
                 "THREADPERFCOUNTER ({}): Counter is being multiplexed", tid);
}

/*
 * This method enables the counters.
 */
void ThreadPerfCounter::start(phase_t starting_phase) {
  counter_debug("THREADPERFCOUNTER ({}): Starting", tid);
  ioctl(fd, PERF_EVENT_IOC_RESET, PERF_IOC_FLAG_GROUP);
  read_counters();
  for (uint i = 0, idx_value = 3;
       i < num_counters && idx_value < num_counter_values;
       i++, idx_value += 2) {
    counters_start[i] = fd_counter_values[idx_value];
    counters_id[i] = fd_counter_values[idx_value + 1];
  }
  ioctl(fd, PERF_EVENT_IOC_ENABLE, PERF_IOC_FLAG_GROUP);
  current_phase = starting_phase;
}

/*
 * This method changes the phase of execution by reading the counters, and then
 * storing their value in the correct place.
 */
void ThreadPerfCounter::change_phase(uint next_phase) {
  counter_debug("THREADPERFCOUNTER ({}): Changing phase: {}", tid, next_phase);
  counter_assert(
      current_phase != DISABLED_PHASE,
      "THREADPERFCOUNTER ({}): Phase cannot be changed for stopped counter",
      tid);
  counter_assert(current_phase != next_phase,
                 "THREADPERFCOUNTER ({}): Cannot change to current phase", tid);
  read_counters();
  for (uint i = 0, idx_value = 3;
       i < num_counters && idx_value < num_counter_values;
       i++, idx_value += 2) {
    counters[i]->update_value(fd_counter_values[idx_value] - counters_start[i],
                              current_phase);
    counters_start[i] = fd_counter_values[idx_value];
    counter_assert(fd_counter_values[idx_value + 1] == counters_id[i],
                   "THREADPERFCOUNTER ({}): Incorrect counter id", tid);
  }
  current_phase = next_phase;
}

/*
 * This method stops/disables the counters.
 */
void ThreadPerfCounter::stop() {
  counter_debug("THREADPERFCOUNTER ({}): Stopping", tid);
  counter_assert(
      current_phase != DISABLED_PHASE,
      "THREADPERFCOUNTER ({}): Counter must be started before stopping", tid);
  change_phase(DISABLED_PHASE);
  ioctl(fd, PERF_EVENT_IOC_DISABLE, PERF_IOC_FLAG_GROUP);
  close(fd);
}

/*
 * This method closes the file descriptor..
 */
void ThreadPerfCounter::close_fd() {
  counter_debug("THREADPERFCOUNTER ({}): Close fd", tid);
  close(fd);
}
