#include "counter_thread.h"

#include "base.h"
#include "common.h"
#include "counter_data.h"

CounterThread::CounterThread(tid_t tid, bool is_gc, AgentState* agent_state)
    : alive(true),
      measuring(false),
      tid(tid),
      is_gc(is_gc),
      agent_state(agent_state) {
  counter_debug(
      "COUNTERTHREAD ({}): Setting up thread without name and counters", tid);
  setup_thread_name();
  setup_counter_data();
  setup_perf_counter();
}

CounterThread::CounterThread(tid_t tid, std::string name, bool is_gc,
                             AgentState* agent_state)
    : alive(true),
      measuring(false),
      tid(tid),
      name(name),
      is_gc(is_gc),
      agent_state(agent_state) {
  counter_debug("COUNTERTHREAD ({}): Setting up thread without counters", tid);
  setup_counter_data();
  setup_perf_counter();
}

CounterThread::CounterThread(tid_t tid, bool is_gc, AgentState* agent_state,
                             CounterData** counters)
    : alive(true),
      measuring(false),
      tid(tid),
      is_gc(is_gc),
      agent_state(agent_state),
      counters(counters) {
  counter_debug("COUNTERTHREAD ({}): Setting up thread without name", tid);
  setup_thread_name();
  setup_perf_counter();
}

CounterThread::CounterThread(tid_t tid, std::string name, bool is_gc,
                             AgentState* agent_state, CounterData** counters)
    : alive(true),
      measuring(false),
      tid(tid),
      name(name),
      is_gc(is_gc),
      agent_state(agent_state),
      counters(counters) {
  counter_debug("COUNTERTHREAD ({}): Setting up thread", tid);
  setup_perf_counter();
}

void CounterThread::start(phase_t start_phase) {
  counter_debug("COUNTERTHREAD ({}): Starting", tid);
  thread_perf_counter->start(start_phase);
  clock_gettime(CLOCK_REALTIME, &curr_time);
  thread_start_time = curr_time.tv_sec * sec_to_ns + curr_time.tv_nsec;
  measuring = true;
}

void CounterThread::change_phase(phase_t next_phase) {
  counter_debug("COUNTERTHREAD ({}): Changing phase: {}", tid, next_phase);
  thread_perf_counter->change_phase(next_phase);
}

void CounterThread::stop() {
  counter_debug("COUNTERTHREAD ({}): Stopping", tid);
  if (measuring == true) {
    thread_perf_counter->stop();
    clock_gettime(CLOCK_REALTIME, &curr_time);
    thread_end_time = curr_time.tv_sec * sec_to_ns + curr_time.tv_nsec;
  } else {
    counter_debug("COUNTERTHREAD ({}): Stopping while not measuring", tid);
    thread_perf_counter->close_fd();
  }
  measuring = false;
}

tid_t CounterThread::get_tid() { return tid; }

CounterData** CounterThread::get_counter_data() { return counters; }

bool CounterThread::get_is_gc() { return is_gc; }

void CounterThread::kill() {
  counter_debug("COUNTERTHREAD ({}): Disabling thread", tid);
  counter_assert(alive == true,
                 "COUNTERTHREAD: Cannot disable threads not enabled");
  alive = false;
}

bool CounterThread::is_alive() { return alive == true; }

YAML::Node CounterThread::to_yaml() {
  YAML::Node node;
  node["NAME"] = name;
  node["GC"] = is_gc;
  node["DURATION"] = thread_end_time - thread_start_time;
  node["COUNTERS"] = get_counter_array_yaml(counters, agent_state);
  return node;
}

void CounterThread::setup_perf_counter() {
  thread_perf_counter = new ThreadPerfCounter(tid, counters, agent_state);
  if (agent_state->get_phase() != DISABLED_PHASE) {
    start(agent_state->get_phase());
  }
}

void CounterThread::setup_counter_data() {
  counters = new CounterData*[MAX_COUNTERS];
  for (uint i = 0; i < agent_state->get_num_events(); i++) {
    counters[i] = new CounterData();
  }
}

void CounterThread::setup_thread_name() {
  name = get_tid_name("/proc/self/task/" + std::to_string(tid));
}
