#ifndef VERIFY_THREAD_H
#define VERIFY_THREAD_H

#include <yaml-cpp/yaml.h>

#include <cstdint>
#include <ctime>
#include <set>
#include <vector>

#include "common.h"

/* This is the buffer size for helper methods that read strings. */
#define VERIFY_CHAR_BUFFER_SIZE 512

/*
 * This is the column number for last executed CPU _after_ the process name.
 * Reference: https://linux.die.net/man/5/proc
 */
#define LAST_EXECUTED_COLUMN_AFTER_NAME 37
#define STATUS_COLUMN_AFTER_NAME 1

class VerifyThread {
  /*  Thread description data that do not change. */
  tid_t tid = 0;
  std::string tid_path;
  std::vector<uint> cpu_mask;

  /*
   * Dyanmic properties of a thread. The name, ideally, should not be dynamic
   * but the JVM changes name after starting threads.
   */
  std::set<uint> cpus_executed;
  std::string name;

  /* A thread is marked dead to prevent it from being analyzed again. */
  bool alive = false;

  /* Keeps track of the last time thread was analyzed, to find dead threads. */
  counter_t last_check = 0;

  /* Thread execution time */
  struct timespec curr_time;
  counter_t thread_start_time = 0;
  counter_t thread_end_time = 0;

  /* Constant multiplier */
  const uint64_t sec_to_ns = 1e9;

  /* Character buffer to read file data */
  char buf[VERIFY_CHAR_BUFFER_SIZE];

  /* The thread does not belong to the JVM, and shouldn't be executing on the
   * same cores as the JVM. */
  bool non_jvm_thread;

  /* Is true, if the thread is setup in the constructor. */
  bool thread_setup;

  /* Number of running count */
  counter_t running_count = 0;

  /* Number of sleep count */
  counter_t sleeping_count = 0;

 public:
  VerifyThread(tid_t tid, std::string tid_path, counter_t current_check_count,
               bool non_jvm_thread);
  void update();
  void kill();
  bool is_alive();
  counter_t get_last_check();
  bool check_if_valid_execution(std::vector<uint>* jvm_cpus,
                                std::vector<uint>* gc_cpus);
  std::string to_string(YAML::Node tid_node);
  YAML::Node to_yaml(std::vector<uint>* jvm_cpus, std::vector<uint>* gc_cpus,
                     counter_t total_time);

 private:
  void set_cpu_mask();
  bool check_if_cpu_mask_has_no_overlap(std::vector<uint>* expected_cpu_mask);
  bool check_if_cpu_mask_equal(std::vector<uint>* expected_cpu_mask);
  bool check_if_execution_cpus_in_mask();
  int get_execution_percent(counter_t total_time);
};

std::string convert_bool_to_string(bool flag);
std::string pad_string(std::string original, uint expected_length);
std::string get_cpu_governor(uint cpu_id);
int get_cpu_frequency(uint cpu_id);

/* Combines the elements of an iterable to a string. */
template <typename Iterable>
std::string convert_iterable_to_string(Iterable start, Iterable end,
                                       std::string start_string,
                                       std::string end_string,
                                       std::string separator) {
  std::string iterable_string = start_string;
  bool pop_back = false;
  while (start != end) {
    std::ostringstream iter_stream;
    iter_stream << *start;
    iterable_string += iter_stream.str();
    iterable_string += separator;
    pop_back = true;
    start++;
  }
  if (pop_back == true) {
    for (uint i = 0; i < separator.length(); i++) {
      iterable_string.pop_back();
    }
  }
  iterable_string += end_string;
  return iterable_string;
}

/* Iterates through an iterable object, and adds them to a YAML node */
template <typename Iterable>
YAML::Node convert_iterable_to_yaml(Iterable start, Iterable end) {
  YAML::Node node;
  uint i = 0;
  while (start != end) {
    node[i] = *start;
    i += 1;
    start++;
  }
  return node;
}

#endif  // VERIFY_THREAD_H
