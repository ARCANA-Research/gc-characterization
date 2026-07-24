#include "counter_manager.h"

CounterManager::CounterManager(AgentState* agent_state)
    : agent_state(agent_state) {}

void CounterManager::add_thread(tid_t tid, bool is_gc) {
  counter_assert(counter_map.find(tid) == counter_map.end(),
                 "COUNTERMANAGER ({}): Thread ID already exists", tid);
  counter_threads.push_back(new CounterThread(tid, is_gc, agent_state));
  counter_map.insert({tid, counter_threads.size() - 1});
}

void CounterManager::add_thread(tid_t tid, bool is_gc, CounterData** counters) {
  counter_assert(counter_map.find(tid) == counter_map.end(),
                 "COUNTERMANAGER ({}): Thread ID already exists", tid);
  counter_threads.push_back(
      new CounterThread(tid, is_gc, agent_state, counters));
  counter_map.insert({tid, counter_threads.size() - 1});
}

void CounterManager::add_thread(tid_t tid, std::string name, bool is_gc) {
  counter_assert(counter_map.find(tid) == counter_map.end(),
                 "COUNTERMANAGER ({}): Thread ID already exists", tid);
  counter_threads.push_back(new CounterThread(tid, name, is_gc, agent_state));
  counter_map.insert({tid, counter_threads.size() - 1});
}

void CounterManager::add_thread(tid_t tid, std::string name, bool is_gc,
                                CounterData** counters) {
  counter_assert(counter_map.find(tid) == counter_map.end(),
                 "COUNTERMANAGER ({}): Thread ID already exists", tid);
  counter_threads.push_back(
      new CounterThread(tid, name, is_gc, agent_state, counters));
  counter_map.insert({tid, counter_threads.size() - 1});
}

std::vector<CounterThread*> CounterManager::get_threads() {
  return counter_threads;
}

void CounterManager::change_phase(phase_t next_phase) {
  for (uint i = 0; i < counter_threads.size(); i++) {
    if (counter_threads[i]->is_alive()) {
      counter_threads[i]->change_phase(next_phase);
    }
  }
}

void CounterManager::start() {
  for (uint i = 0; i < counter_threads.size(); i++) {
    if (counter_threads[i]->is_alive()) {
      counter_threads[i]->start(MUTATOR_PHASE);
    }
  }
}

void CounterManager::stop() {
  for (uint i = 0; i < counter_threads.size(); i++) {
    if (counter_threads[i]->is_alive()) {
      counter_threads[i]->stop();
    }
  }
}

void CounterManager::thread_end(tid_t tid) {
  counter_assert(counter_map.find(tid) != counter_map.end(),
                 "COUNTERMANAGER ({}): Thread ID not found", tid);
  uint tid_idx = counter_map.at(tid);
  counter_threads[tid_idx]->stop();
  counter_threads[tid_idx]->kill();
}

YAML::Node CounterManager::to_yaml() {
  YAML::Node threads_node;
  for (uint i = 0; i < counter_threads.size(); i++) {
    threads_node[counter_threads[i]->get_tid()] = counter_threads[i]->to_yaml();
  }
  return threads_node;
}

void CounterManager::sum_counters(CounterData** jvm_counters,
                                  CounterData** gc_counters) {
  for (uint i = 0; i < counter_threads.size(); i++) {
    if (counter_threads[i]->get_is_gc()) {
      add_counter_data_array_to_another(
          gc_counters, counter_threads[i]->get_counter_data(), agent_state);
    } else {
      add_counter_data_array_to_another(
          jvm_counters, counter_threads[i]->get_counter_data(), agent_state);
    }
  }
}
