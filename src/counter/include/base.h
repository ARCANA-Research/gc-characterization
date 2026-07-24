#ifndef counter_BASE_H
#define counter_BASE_H

#include <classfile_constants.h>
#include <jni.h>
#include <jvmti.h>
#include <perfmon/pfmlib.h>
#include <perfmon/pfmlib_perf_event.h>
#include <yaml-cpp/yaml.h>

#include <cstdint>
#include <string>

#include "common.h"

/* ================================ CONSTANTS =============================== */
/*
 * We define 3 base phases that are used by the agent. The JVM can signal up-to
 * 26 phases. The current phase of execution is stored in
 * {@code benchmark_phase}.
 */
#define DISABLED_PHASE 0
#define MUTATOR_PHASE 1
#define GC_STW_PHASE 2

/* This is the buffer size for helper methods that read strings. */
#define CHAR_BUFFER_SIZE 64

/* Maximum number of types of performance counters measured. */
#define MAX_COUNTERS 8

/* ============================= HELPER METHODS ============================= */

/*
 * Helper methods used by the toolkit to sanity check the state of execution.
 */

/* Make sure that multiple instances of the library aren't loaded */
void check_if_single_threaded();

/* This is needed to read some performance counters */
void check_event_paranoid();

/* Helper method that outputs a YAML node to the statistics output file. */
void save_yaml(YAML::Node node);
void save_yaml_path(YAML::Node node, std::string yaml_path);

/* Helper functions used for setting up counters. */
int get_perf_event_type(std::string event_name);

/* Helper method to et name of thread. */
std::string get_tid_name(std::string tid_path, bool throw_exception = false);

/* Helper method to check if thread is GC. */
bool is_gc_tid(std::string tid_name);

/* Returns the tid of a thread from its path. */
tid_t get_tid(std::string tid_path);

/* ============================= DACAPO TRIGGERS ============================ */

/*
 * Used by DaCapo to signal start and end of benchmark execution.
 */

/*
 * Trigger: DaCapo benchmark start
 */
extern "C" void start_roi(jlong _tls);

/*
 * Trigger: DaCapo benchmark end
 */
extern "C" void stop_roi(jlong _tls);

/* =============================== JVMTI SETUP ============================== */

/*
 * This method is called on JVM start, and sets up all JVMTI calls used by the
 * counter toolkit.
 */
JNIEXPORT jint JNICALL Agent_OnLoad(JavaVM* jvm, char* opts, void* reserved);

/* ============================ LIBRARY TRIGGERS ============================ */

/*
 * Used by JVMTI agent to switch execution phases, and save output.
 */

/*
 * This method is called when the library is loaded. We perform sanity checks,
 * and initialize the performance counter toolkit.
 */
void setup();

/*
 * Change execution phases for all counters in the agent.
 */
void execution_change_phase(phase_t next_phase);

/*
 * Save counter values.
 */
void write_stats();

/*
 * Basic setup checks for all agents.
 */
void sanity_checks(std::string agent_name, bool per_thread_measurement,
                   bool per_thread_data, bool concurrent_gc_measured,
                   bool performance_counters_measured, bool per_phase_counter);

#endif  // counter_BASE_H
