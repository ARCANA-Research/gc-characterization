#include "base.h"

#include <pthread.h>

#include <cstring>
#include <fstream>

#include "common.h"

/*
 * Checks if event paranoid is set correctly for the toolkit.
 */
void check_event_paranoid() {
  char buf[CHAR_BUFFER_SIZE];
  FILE* f = fopen("/proc/sys/kernel/perf_event_paranoid", "r");
  if (!f) {
    counter_assert(false,
                   "SETUP: /proc/sys/kernel/perf_event_paranoid not found");
  }
  while (fgets(buf, CHAR_BUFFER_SIZE, f)) {
    int val = atoi(buf);
    if (val == -1) {
      fclose(f);
      return;
    }
  }
  fclose(f);
  counter_assert(
      false, "SETUP: /proc/sys/kernel/perf_event_paranoid should be set to -1");
}

/*
 * Checks if the toolkit was started with LD_PRELOAD.
 */
void check_if_single_threaded() {
  char buf[CHAR_BUFFER_SIZE];
  FILE* f = fopen("/proc/self/status", "r");
  counter_assert(f, "SETUP: /proc/self/status not found");
  int thread_count;
  int pid;
  while (fgets(buf, CHAR_BUFFER_SIZE, f)) {
    if (std::strncmp(buf, "Pid", 3) == 0) {
      char* c = buf + 5;
      sscanf(c, "%d", &pid);
    }
    if (std::strncmp(buf, "Threads", 7) == 0) {
      char* c = buf + 9;
      sscanf(c, "%d", &thread_count);
    }
  }
  fclose(f);
  counter_assert(thread_count == 1, "SETUP: Run with LD_PRELOAD");
  printf("AGENT PID: %d\n", pid);
}

/* Returns the name of a thread. */
std::string get_tid_name(std::string tid_path, bool throw_exception) {
  tid_path += "/status";
  char buf[CHAR_BUFFER_SIZE];
  FILE* f = fopen(tid_path.c_str(), "r");
  if (!f) {
    if (throw_exception == true) {
      counter_test(f, "SETUP: Could not open tid status file ({}, {})",
                   strerror(errno), tid_path);
    } else {
      counter_assert(f, "SETUP: Could not open tid status file ({}, {})",
                     strerror(errno), tid_path);
    }
  }
  while (fgets(buf, CHAR_BUFFER_SIZE, f)) {
    if (std::strncmp(buf, "Name", 4) == 0) {
      char* c = buf + 6;
      std::string tid_name(c);
      fclose(f);
      if (tid_name[tid_name.length() - 1] == '\n') {
        tid_name.erase(tid_name.length() - 1);
      }
      return tid_name;
    }
  }
  fclose(f);
  return "UNKNOWN";
}

/* Returns the tid of a thread from its path. */
tid_t get_tid(std::string tid_path) {
  return std::stoi(tid_path.erase(0, tid_path.rfind("/") + 1));
}

/* Helper method to check if thread is GC. */
bool is_gc_tid(std::string tid_name) {
  return tid_name.find("GC:") != std::string::npos;
}

/* Write stats to file. */
void save_yaml(YAML::Node node) {
  std::string stats_save_path = getenv("COUNTER_STATS_FILE");
  save_yaml_path(node, stats_save_path);
}

/* Write stats to file. */
void save_yaml_path(YAML::Node node, std::string yaml_path) {
  counter_debug("AGENT: Saving -> {}", yaml_path.c_str());
  std::ofstream f(yaml_path);
  f << node;
  f.close();
}

/* Basic setup checks for all agents. */
void sanity_checks(std::string agent_type) {
  printf("COUNTER: %s\n", agent_type.c_str());

  check_if_single_threaded();
  check_event_paranoid();
}

void sanity_checks(std::string agent_name, bool per_thread_measurement,
                   bool per_thread_data, bool concurrent_gc_measured,
                   bool performance_counters_measured, bool per_phase_counter) {
#if DEBUG_LOG
  spdlog::set_level(spdlog::level::debug);
#else
  spdlog::set_level(spdlog::level::info);
#endif

  printf("COUNTER: %s\n", agent_name.c_str());

#if DEBUG_LOG
  printf("✅ DEBUG ENABLED\n");
#else
  printf("❌ DEBUG ENABLED\n");
#endif

#if USE_COUNTER_GC_EVENTS
  printf("✅ COUNTER GC EVENTS\n");
#else
  printf("❌ COUNTER GC EVENTS\n");
#endif

  if (per_thread_measurement) {
    printf("✅ PER THREAD MEASUREMENT\n");
  } else {
    printf("❌ PER THREAD MEASUREMENT\n");
  }

  if (per_thread_data) {
    printf("✅ PER THREAD DATA\n");
  } else {
    printf("❌ PER THREAD DATA\n");
  }

  if (concurrent_gc_measured) {
    printf("✅ CONCURRENT GC\n");
  } else {
    printf("❌ CONCURRENT GC\n");
  }

  if (performance_counters_measured) {
    printf("✅ PERFORMANCE COUNTERS\n");
  } else {
    printf("❌ PERFORMANCE COUNTERS\n");
  }

  if (per_phase_counter) {
    printf("✅ PER PHASE COUNTERS\n");
  } else {
    printf("❌ PER PHASE COUNTERS\n");
  }

  check_if_single_threaded();
  check_event_paranoid();
}

/* Get type of perf event. */
int get_perf_event_type(std::string event_name) {
  if (event_name.find("RAPL") != std::string::npos) {
    return PERF_TYPE_HARDWARE;
  }
  if (event_name.find("PERF_COUNT_HW") != std::string::npos) {
    return PERF_TYPE_HARDWARE;
  }
  if (event_name.find("PERF_COUNT_SW") != std::string::npos) {
    return PERF_TYPE_SOFTWARE;
  }
  return PERF_TYPE_RAW;
}
