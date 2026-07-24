#ifndef INHERIT_PERF_COUNTER_H
#define INHERIT_PERF_COUNTER_H

#include <perfmon/pfmlib.h>
#include <perfmon/pfmlib_perf_event.h>

#include <cstdint>

#include "agent_state.h"
#include "base.h"
#include "counter_data.h"

/* Maximum number of values that will be read from the counter file. */
#define INHERIT_PERF_READ_VALUES 4

/*
 * {@code InheritPerfCounter} class contains the logic for reading performance
 * counters where child processes inherit this counter. It is primarily used
 * for estimating the overhead of complete JVM as its TID is fixed to 0. It
 * writes to a specific {@code CounterData} pointer.
 */
class InheritPerfCounter {
  /* Performance counter file descriptor per counter */
  int fd[MAX_COUNTERS];

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

  /* Performance counter values read */
  counter_t fd_counter_values[INHERIT_PERF_READ_VALUES];
  uint num_counters = 0;
  int64_t size_counter_values = 0;

 public:
  InheritPerfCounter(CounterData **counters, AgentState *agent_state);
  void read_counter(uint counter_idx);
  void start(phase_t starting_phase);
  void change_phase(phase_t next_phase);
  void stop();
};

#endif  // INHERIT_PERF_COUNTER_H
