#include "jvm_execution.h"

#include "base.h"
#include "common.h"

JvmExecution::JvmExecution(AgentState* agent_state) : agent_state(agent_state) {
  counter_debug("JVMEXECUTION: Setting up execution counter");
  counters = new CounterData*[MAX_COUNTERS];
  for (uint i = 0; i < agent_state->get_num_events(); i++) {
    counters[i] = new CounterData();
  }
  inherit_perf_counter = new InheritPerfCounter(counters, agent_state);
}

void JvmExecution::start() {
  counter_debug("JVMEXECUTION: Starting");
  inherit_perf_counter->start(MUTATOR_PHASE);
}

void JvmExecution::change_phase(phase_t next_phase) {
  counter_debug("JVMEXECUTION: Changing phase");
  inherit_perf_counter->change_phase(next_phase);
}

void JvmExecution::stop() {
  counter_debug("JVMEXECUTION: Stopping");
  inherit_perf_counter->stop();
}

CounterData** JvmExecution::get_counter_data() { return counters; }
