#ifndef counter_THREAD_H
#define counter_THREAD_H

#include <yaml-cpp/yaml.h>

#include <ctime>
#include <string>

#include "agent_state.h"
#include "base.h"
#include "counter_data.h"
#include "thread_perf_counter.h"

/*
 * {@code CounterThread} class defines a thread whose performance counters are
 * measured by our tool.
 */
class CounterThread {
  /* Thread related information */
  bool alive = false;
  bool measuring = false;
  tid_t tid = 0;
  std::string name;
  bool is_gc = false;

  /* Thread execution information */
  struct timespec curr_time;
  counter_t thread_start_time = 0;
  counter_t thread_end_time = 0;
  AgentState* agent_state = nullptr;

  /* {@code CounterData} where counter values are written. */
  CounterData** counters = nullptr;

  /* Performance counter associated with the thread */
  ThreadPerfCounter* thread_perf_counter = nullptr;

  /* Constant multiplier */
  uint64_t sec_to_ns = 1e9;

 public:
  CounterThread(tid_t tid, bool is_gc, AgentState* agent_state);
  CounterThread(tid_t tid, bool is_gc, AgentState* agent_state,
                CounterData** counters);
  CounterThread(tid_t tid, std::string name, bool is_gc,
                AgentState* agent_state);
  CounterThread(tid_t tid, std::string name, bool is_gc,
                AgentState* agent_state, CounterData** counters);
  tid_t get_tid();
  CounterData** get_counter_data();
  bool get_is_gc();
  void kill();
  bool is_alive();
  void start(phase_t start_phase);
  void change_phase(phase_t next_phase);
  void stop();
  YAML::Node to_yaml();

 private:
  void setup_perf_counter();
  void setup_counter_data();
  void setup_thread_name();
};

#endif  // counter_THREAD_H
