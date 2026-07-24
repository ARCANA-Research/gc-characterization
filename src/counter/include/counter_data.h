#ifndef COUNTER_DATA_H
#define COUNTER_DATA_H

#include <yaml-cpp/yaml.h>

#include "agent_state.h"
#include "base.h"

/* Maximum number of types of GC phases. */
#define NUM_PHASES 27

/*
 * {@code CounterData} class is the base class for all counters used in our
 * code. Each counter consists of the current phase start value, its total past
 * values, and an {@code id}. The {@code id} is used by performance counters.
 */
class CounterData {
  counter_t values[NUM_PHASES];

 public:
  CounterData();
  virtual void update_value(counter_t value, phase_t phase);
  virtual counter_t get_value(phase_t phase);
  virtual YAML::Node to_yaml();
};

/*
 * Generate YAML node for an array of counters.
 */
YAML::Node get_counter_array_yaml(CounterData** counters,
                                  AgentState* agent_state);

/*
 * Generate YAML node for an array of counters.
 */
void add_counter_data_array_to_another(CounterData** A_counters,
                                       CounterData** B_counters,
                                       AgentState* agent_state);

#endif  // COUNTER_DATA_H
