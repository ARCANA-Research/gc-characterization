#ifndef AGENT_COUNTER_H
#define AGENT_COUNTER_H

#include <yaml-cpp/yaml.h>

#include <ctime>

#include "base.h"
#include "counter_data.h"
#include "counter_thread.h"
#include "per_phase_counter_data.h"

/*
 * {@code AgentCounterGroup} class defines all counters measured by the
 * analysis tool: time, event count, and thread count. All of these counters
 * are measured and cannot be selectively enabled/disabled to simplify library
 * logic, and improve performance.
 */
class AgentCounterGroup {
  /* Time-related metrics for GC-events */
  struct timespec curr_time;
  CounterData* time_counter = nullptr;
  counter_t time_start = 0;

  /* How often GC-events are triggerred */
  CounterData* gc_counter = nullptr;

  /* Track current phase for sanity checks */
  phase_t current_phase = 0;

  /* Constant multiplier */
  const uint64_t sec_to_ns = 1e9;

 public:
  /* Constructor without per phase time counter */
  AgentCounterGroup() : AgentCounterGroup(false) {};
  AgentCounterGroup(bool per_phase_counter);
  void start();
  void change_phase(phase_t next_phase);
  void stop();
  YAML::Node to_yaml();
  YAML::Node to_yaml(std::vector<CounterThread*> threads);
};

#endif  // AGENT_COUNTER_H
