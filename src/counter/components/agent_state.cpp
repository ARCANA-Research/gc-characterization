#include "agent_state.h"

/*
 * {@code AgentState} constructor initializes the state of execution
 */
AgentState::AgentState(std::vector<std::string> perf_events)
    : phase(DISABLED_PHASE),
      roi(false),
      finished(false),
      perf_events(perf_events) {}

void AgentState::start() {
  roi = true;
  phase = MUTATOR_PHASE;
  finished = false;
}

void AgentState::change_phase(phase_t new_phase) { phase = new_phase; }

void AgentState::stop() {
  roi = false;
  phase = DISABLED_PHASE;
  finished = true;
}

bool AgentState::in_roi() { return roi; }

bool AgentState::is_same_phase(phase_t new_phase) { return phase == new_phase; }

uint AgentState::get_num_events() { return perf_events.size(); }

std::string AgentState::get_event(uint idx) { return perf_events[idx]; }

phase_t AgentState::get_phase() { return phase; }

bool AgentState::is_finished() { return finished; }

void AgentState::set_gc_cpus(std::vector<uint> _gc_cpus,
                             bool remove_smt_lanes) {
  for (uint i = 0; i < _gc_cpus.size(); i++) {
    uint curr_cpu = _gc_cpus[i];
    if (curr_cpu > NUM_CPU_CORES) {
      if (std::find(gc_cpus.begin(), gc_cpus.end(), curr_cpu - NUM_CPU_CORES) ==
          gc_cpus.end()) {
        gc_cpus.push_back(curr_cpu);
      }
    } else {
      if (std::find(gc_cpus.begin(), gc_cpus.end(), curr_cpu + NUM_CPU_CORES) ==
          gc_cpus.end()) {
        gc_cpus.push_back(curr_cpu);
      }
    }
  }
}

uint AgentState::get_num_gc_cpu() { return gc_cpus.size(); }

uint AgentState::get_gc_cpu(uint idx) { return gc_cpus[idx]; }

void AgentState::set_jvm_cpus(std::vector<uint> _jvm_cpus,
                              bool remove_smt_lanes) {
  for (uint i = 0; i < _jvm_cpus.size(); i++) {
    uint curr_cpu = _jvm_cpus[i];
    if (curr_cpu > NUM_CPU_CORES) {
      if (std::find(jvm_cpus.begin(), jvm_cpus.end(),
                    curr_cpu - NUM_CPU_CORES) == jvm_cpus.end()) {
        jvm_cpus.push_back(curr_cpu);
      }
    } else {
      if (std::find(jvm_cpus.begin(), jvm_cpus.end(),
                    curr_cpu + NUM_CPU_CORES) == jvm_cpus.end()) {
        jvm_cpus.push_back(curr_cpu);
      }
    }
  }
}

uint AgentState::get_num_jvm_cpu() { return jvm_cpus.size(); }

uint AgentState::get_jvm_cpu(uint idx) { return jvm_cpus[idx]; }
