#ifndef PER_PHASE_COUNTER_DATA_H
#define PER_PHASE_COUNTER_DATA_H

#include <yaml-cpp/yaml.h>

#include "base.h"
#include "counter_data.h"

/*
 * {@code PerPhaseCounterData} class implement per-phase counters used for
 * finger grained analysis. The class stores all phases of execution, and the
 * measured cost for these phases.
 */
class PerPhaseCounterData : public CounterData {
  std::vector<counter_t> values;
  std::vector<phase_t> phases;
  counter_t total_values[NUM_PHASES];

 public:
  PerPhaseCounterData();
  void update_value(counter_t value, phase_t phase) override;
  counter_t get_value(phase_t phase) override;
  YAML::Node to_yaml() override;
};

#endif  // PER_PHASE_COUNTER_DATA_H
