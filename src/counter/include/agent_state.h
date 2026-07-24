#ifndef AGENT_STATE_H
#define AGENT_STATE_H

#include <string>
#include <vector>

#include "base.h"

#define NUM_CPU_CORES 24

/*
 * {@code AgentState} class stores data related to the state of execution.
 */
class AgentState {
  phase_t phase = 0;
  bool roi = false;
  bool finished = false;
  std::vector<std::string> perf_events;
  std::vector<uint> gc_cpus;
  std::vector<uint> jvm_cpus;

 public:
  AgentState(std::vector<std::string> perf_events);
  void start();
  void change_phase(phase_t new_phase);
  void stop();
  bool in_roi();
  bool is_same_phase(phase_t new_phase);
  uint get_num_events();
  std::string get_event(uint idx);
  phase_t get_phase();
  bool is_finished();
  void set_gc_cpus(std::vector<uint> gc_cpus, bool remove_smt_lanes);
  uint get_num_gc_cpu();
  uint get_gc_cpu(uint idx);
  void set_jvm_cpus(std::vector<uint> gc_cpus, bool remove_smt_lanes);
  uint get_num_jvm_cpu();
  uint get_jvm_cpu(uint idx);
};

#endif  // AGENT_STATE_H
