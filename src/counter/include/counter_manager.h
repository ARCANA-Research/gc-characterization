#ifndef counter_MANAGER_H
#define counter_MANAGER_H

#include <yaml-cpp/yaml.h>

#include <map>
#include <vector>

#include "agent_state.h"
#include "base.h"
#include "counter_data.h"
#include "counter_thread.h"

/*
 * {@code CounterManager} class manages Counter threads.
 */
class CounterManager {
  /* Vector of threads */
  std::vector<CounterThread*> counter_threads;
  std::map<tid_t, uint> counter_map;
  AgentState* agent_state;

 public:
  CounterManager(AgentState* agent_state);
  void add_thread(tid_t tid, bool is_gc);
  void add_thread(tid_t tid, bool is_gc, CounterData** counters);
  void add_thread(tid_t tid, std::string name, bool is_gc);
  void add_thread(tid_t tid, std::string name, bool is_gc,
                  CounterData** counters);
  std::vector<CounterThread*> get_threads();
  void change_phase(phase_t next_phase);
  void start();
  void stop();
  void thread_end(tid_t tid);
  YAML::Node to_yaml();
  void sum_counters(CounterData** jvm_counters, CounterData** gc_counters);
};

#endif  // counter_MANAGER_H
