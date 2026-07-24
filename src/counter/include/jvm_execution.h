#ifndef JVM_EXECUTION_H
#define JVM_EXECUTION_H

#include "agent_state.h"
#include "base.h"
#include "counter_data.h"
#include "inherit_perf_counter.h"

/*
 * {@code JvmExecution} class defines counters that measure complete execution
 */
class JvmExecution {
  /* Execution information */
  AgentState *agent_state = nullptr;

  /* {@code CounterData} where counter values are written. */
  CounterData **counters = nullptr;

  /* Performance counter associated with the thread */
  InheritPerfCounter *inherit_perf_counter = nullptr;

 public:
  JvmExecution(AgentState *agent_state);
  CounterData **get_counter_data();
  void start();
  void change_phase(phase_t next_phase);
  void stop();
};

#endif  // JVM_EXECUTION_H
