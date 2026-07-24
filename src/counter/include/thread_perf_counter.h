#ifndef PERF_COUNTER_H
#define PERF_COUNTER_H

#include <perfmon/pfmlib.h>
#include <perfmon/pfmlib_perf_event.h>

#include <cstdint>

#include "agent_state.h"
#include "base.h"
#include "counter_data.h"

/* Maximum number of values that will be read from the counter file. */
#define MAX_THREAD_PERF_READ_VALUES 16

/*
 * {@code ThreadPerfCounter} class contains the logic for reading performance
 * counters. It writes to a specific {@code CounterData} pointer.
 */
class ThreadPerfCounter {
  /* Performance counter open information */
  int fd = -1;

  /* {@code CounterData} where counter values are written. */
  CounterData **counters = nullptr;

  /*
   * We store start, and id values separately as multiple counters can share
   * a single data structure.
   */
  counter_t counters_start[MAX_COUNTERS];
  counter_t counters_id[MAX_COUNTERS];

  /* Track current phase for sanity checks */
  phase_t current_phase = 0;

  /* Thread ID of thread being measured */
  tid_t tid = 0;

  /* Performance counter values read */
  counter_t fd_counter_values[MAX_THREAD_PERF_READ_VALUES];
  uint num_counters = 0;
  uint num_counter_values = 0;
  int64_t size_counter_values = 0;

 public:
  ThreadPerfCounter(tid_t tid, CounterData **counters, AgentState *agent_state);
  void read_counters();
  void start(phase_t starting_phase);
  void change_phase(phase_t next_phase);
  void stop();
  void close_fd();
};

/* Helper functions used for setting up counters. */
int get_perf_event_type(std::string event_name);

#endif  // PERF_COUNTER_H
