#include <classfile_constants.h>
#include <jni.h>
#include <jvmti.h>

#include "agent_counter.h"
#include "agent_state.h"
#include "common.h"
#include "jvmti_pause.h"

/* ============================ GLOBAL VARIABLES ============================ */

/* Some variables used for tracking state of execution. */
AgentState* agent_state;

/* Global variable that defines counters measured by the toolkit. */
AgentCounterGroup* agent_group;

/* ============================== AGENT METHODS ============================= */

__attribute__((constructor)) void setup() {
  sanity_checks("PER_PHASE_AGENT", false, false, false, false, true);

  agent_group = new AgentCounterGroup(true);
  agent_state = new AgentState(std::vector<std::string>());
}

void write_stats() {
  YAML::Node node;
  node["AGENT"] = agent_group->to_yaml();
  node["JVM"] = YAML::Node();
  node["GC"] = YAML::Node();
  node["THREADS"] = YAML::Node();
  save_yaml(node);
}

/*
 * Change execution phases for all counters in the agent.
 */
void execution_change_phase(phase_t new_phase) {
  if (agent_state->is_same_phase(new_phase)) {
    counter_debug("AGENT: Cannot change to current phase");
    return;
  }
  if (agent_state->in_roi() == false) {
    counter_debug("AGENT: Cannot change as not in ROI");
    return;
  }
  counter_debug("AGENT: New phase {}", new_phase);
  agent_group->change_phase(new_phase);
  agent_state->change_phase(new_phase);
}

/* ============================= JVMTI CALLBACKS ============================ */

extern "C" void start_roi(jlong _tls) {
  agent_state->start();
  agent_group->start();
}

extern "C" void stop_roi(jlong _tls) {
  agent_group->stop();
  agent_state->stop();
  write_stats();
}
