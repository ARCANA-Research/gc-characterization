#include "counter_data.h"

/*
 * {@code CounterData} constructor initializes values, start value, and id to
 * zero.
 */
CounterData::CounterData() {
  for (phase_t i = 0; i < NUM_PHASES; i++) {
    values[i] = 0;
  }
}

/*
 * Update the value of a counter for a phase {@code phase}.
 */
void CounterData::update_value(counter_t value, phase_t phase) {
  values[phase] += value;
}

/*
 * Get the value of a counter for a specific phase.
 */
counter_t CounterData::get_value(phase_t phase) { return values[phase]; }

/*
 * This method returns the values of the counter in YAML format.
 */
YAML::Node CounterData::to_yaml() {
  YAML::Node node;
  for (phase_t p = 0; p < NUM_PHASES; p++) {
    node[p] = values[p];
  }
  return node;
}

/*
 * Generate YAML node for an array of counters.
 */
YAML::Node get_counter_array_yaml(CounterData **counters,
                                  AgentState *agent_state) {
  YAML::Node node;
  for (uint i = 0; i < agent_state->get_num_events(); i++) {
    node[agent_state->get_event(i)] = counters[i]->to_yaml();
  }
  return node;
}

/*
 * Generate YAML node for an array of counters.
 */
void add_counter_data_array_to_another(CounterData **A_counters,
                                       CounterData **B_counters,
                                       AgentState *agent_state) {
  for (uint i = 0; i < agent_state->get_num_events(); i++) {
    for (uint j = 0; j < NUM_PHASES; j++) {
      A_counters[i]->update_value(B_counters[i]->get_value(j), j);
    }
  }
}
