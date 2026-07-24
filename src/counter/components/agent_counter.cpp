#include "agent_counter.h"

#include "common.h"

/*
 * {@code AgentCounterGroup} constructor initializes event counter arrays and
 * sets the execution phase, for the counters, to disabled. It also initliazes
 * all counters with the goal of preventing memory allocation operations later
 * in benchmark execution. This constructor allows for per-phase time counter.
 */
AgentCounterGroup::AgentCounterGroup(bool per_phase_counter) {
  if (per_phase_counter) {
    counter_debug("AGENTCOUNTERGROUP: Per Phase Initialized");
    time_counter = new PerPhaseCounterData();
  } else {
    counter_debug("AGENTCOUNTERGROUP: Initialized");
    time_counter = new CounterData();
  }
  gc_counter = new CounterData();
  current_phase = DISABLED_PHASE;
}

/*
 * Start is called on VM Start event, and initializes the time counter, and
 * switches to mutator execution execution phase.
 */
void AgentCounterGroup::start() {
  counter_debug("AGENTCOUNTERGROUP: Starting");
  clock_gettime(CLOCK_REALTIME, &curr_time);
  time_start = curr_time.tv_sec * sec_to_ns + curr_time.tv_nsec;
  current_phase = MUTATOR_PHASE;
}

/*
 * This method is called on any phase change, and updates counter values as
 * needed.
 */
void AgentCounterGroup::change_phase(phase_t next_phase) {
  counter_assert(
      current_phase != DISABLED_PHASE,
      "AGENTCOUNTERGROUP: Phase cannot be changed for stopped counter");
  counter_assert(current_phase != next_phase,
                 "AGENTCOUNTERGROUP: Cannot change to current phase");
  counter_debug("AGENTCOUNTERGROUP: Changing phase {}", next_phase);
  clock_gettime(CLOCK_REALTIME, &curr_time);
  counter_t curr_time_ns = curr_time.tv_sec * sec_to_ns + curr_time.tv_nsec;
  time_counter->update_value(curr_time_ns - time_start, current_phase);
  time_start = curr_time_ns;
  gc_counter->update_value(1, current_phase);
  current_phase = next_phase;
}

/*
 * This method is called when benchmark finishes.
 */
void AgentCounterGroup::stop() {
  counter_debug("AGENTCOUNTERGROUP: Stopping");
  counter_assert(current_phase != DISABLED_PHASE,
                 "AGENTCOUNTERGROUP: Counter must be started before stopping");
  change_phase(DISABLED_PHASE);
}

/*
 * This method returns the values of the counters in YAML format.
 */
YAML::Node AgentCounterGroup::to_yaml() {
  counter_debug("AGENTCOUNTERGROUP: Saving output");
  YAML::Node node;
  node["TIME"] = time_counter->to_yaml();
  node["GC_EVENT_COUNT"] = gc_counter->to_yaml();
  node["GC_THREAD_COUNT"] = YAML::Node();
  node["GC_THREADS"] = YAML::Node();
  node["JVM_THREAD_COUNT"] = YAML::Node();
  node["JVM_THREADS"] = YAML::Node();
  return node;
}

/*
 * This method returns the values of the counters in YAML format.
 */
YAML::Node AgentCounterGroup::to_yaml(std::vector<CounterThread*> threads) {
  counter_debug("AGENTCOUNTERGROUP: Saving output");
  YAML::Node node;
  node["TIME"] = time_counter->to_yaml();
  node["GC_EVENT_COUNT"] = gc_counter->to_yaml();
  std::vector<tid_t> gc_threads;
  std::vector<tid_t> jvm_threads;
  for (uint i = 0; i < threads.size(); i++) {
    if (threads[i]->get_is_gc()) {
      gc_threads.push_back(threads[i]->get_tid());
    } else {
      jvm_threads.push_back(threads[i]->get_tid());
    }
  }
  node["GC_THREAD_COUNT"] = gc_threads.size();
  node["GC_THREADS"] = gc_threads;
  node["JVM_THREAD_COUNT"] = jvm_threads.size();
  node["JVM_THREADS"] = jvm_threads;
  return node;
}
