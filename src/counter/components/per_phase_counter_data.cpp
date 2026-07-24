#include "per_phase_counter_data.h"

/*
 * {@code PerPhaseCounterData} constructor initializes total values to zero.
 */
PerPhaseCounterData::PerPhaseCounterData() {
  for (phase_t i = 0; i < NUM_PHASES; i++) {
    total_values[i] = 0;
  }
}

/*
 * Update the value of a counter for a phase {@code phase}.
 */
void PerPhaseCounterData::update_value(counter_t value, phase_t phase) {
  values.push_back(value);
  phases.push_back(phase);
  total_values[phase] += value;
}

/*
 * Return total value for a phase.
 */
counter_t PerPhaseCounterData::get_value(phase_t phase) {
  return total_values[phase];
}

/*
 * This method returns the values of the counter in YAML format.
 */
YAML::Node PerPhaseCounterData::to_yaml() {
  YAML::Node node;
  node["values"] = values;
  node["phases"] = phases;
  YAML::Node total;
  for (phase_t p = 0; p < NUM_PHASES; p++) {
    total[p] = total_values[p];
  }
  node["total"] = total;
  return node;
}
