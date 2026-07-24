#include <classfile_constants.h>
#include <fcntl.h>
#include <jni.h>
#include <jvmti.h>
#include <unistd.h>

#include <filesystem>

#include "agent_counter.h"
#include "agent_state.h"
#include "common.h"
#include "counter_data.h"
#include "counter_manager.h"
#include "jvm_execution.h"
#include "jvmti_concurrent.h"
#include "msr_control.h"

/* ============================ GLOBAL VARIABLES ============================ */

AgentState* agent_state;
AgentCounterGroup* agent_group;

JvmExecution* jvm_execution;

CounterManager* gc_threads;
CounterData* gc_counters[MAX_COUNTERS];

/* ============================== AGENT METHODS ============================= */

__attribute__((constructor)) void setup() {
  thread_mutex.lock();

  sanity_checks("NO_PREFETCHER_STW", false, false, true, true, false);

  /* Initialize libpfm; which is used to parse performance counter names */
  int ret = pfm_initialize();
  counter_assert(ret == PFM_SUCCESS, pfm_strerror(ret));

  agent_group = new AgentCounterGroup();

  /* Read performance counters */
  YAML::Node counters_node = YAML::LoadFile(getenv("COUNTER_FILE"));
  std::vector<std::string> perf_counter =
      counters_node["PERF"]["counters"].as<std::vector<std::string>>();
  agent_state = new AgentState(perf_counter);

  /* Analyze JVM with PID 0 to analyze the complete counters for all threads. */
  for (uint i = 0; i < agent_state->get_num_events(); i++) {
    gc_counters[i] = new CounterData();
  }
  jvm_execution = new JvmExecution(agent_state);
  gc_threads = new CounterManager(agent_state);

  /* Disable L2 prefetcher for GC cores */
  agent_state->set_gc_cpus(counters_node["gc-cpus"].as<std::vector<uint>>(),
                           true);
  agent_state->set_jvm_cpus(counters_node["jvm-cpus"].as<std::vector<uint>>(),
                            true);
  for (uint i = 0; i < agent_state->get_num_gc_cpu(); i++) {
    uint gc_cpu = agent_state->get_gc_cpu(i);
    disable_prefetcher(gc_cpu);
  }
  for (uint i = 0; i < agent_state->get_num_jvm_cpu(); i++) {
    uint jvm_cpu = agent_state->get_jvm_cpu(i);
    enable_prefetcher(jvm_cpu);
  }

  thread_mutex.unlock();
}

void write_stats() {
  YAML::Node node;
  node["AGENT"] = agent_group->to_yaml(gc_threads->get_threads());
  node["JVM"] =
      get_counter_array_yaml(jvm_execution->get_counter_data(), agent_state);
  node["GC"] = get_counter_array_yaml(gc_counters, agent_state);
  node["THREADS"] = YAML::Node();
  save_yaml(node);
}

void execution_change_phase(phase_t new_phase) {
  if (agent_state->is_same_phase(new_phase)) {
    counter_debug("AGENT: Cannot change to current phase");
    return;
  }
  if (agent_state->in_roi() == false) {
    counter_debug("AGENT: Cannot change as not in ROI");
    return;
  }
  if (new_phase < 2) {
    /* Enable Prefetcher */
    for (uint i = 0; i < agent_state->get_num_jvm_cpu(); i++) {
      uint jvm_cpu = agent_state->get_jvm_cpu(i);
      enable_prefetcher(jvm_cpu);
    }
  } else {
    /* Disable Prefetcher */
    for (uint i = 0; i < agent_state->get_num_jvm_cpu(); i++) {
      uint jvm_cpu = agent_state->get_jvm_cpu(i);
      disable_prefetcher(jvm_cpu);
    }
  }
  counter_debug("AGENT: New phase {}", new_phase);
  agent_group->change_phase(new_phase);
  jvm_execution->change_phase(new_phase);
  gc_threads->change_phase(new_phase);
  agent_state->change_phase(new_phase);
}

/* ============================= JVMTI CALLBACKS ============================ */

extern "C" void start_roi(jlong _tls) {
  thread_mutex.lock();

  agent_state->start();
  agent_group->start();
  jvm_execution->start();
  gc_threads->start();

  thread_mutex.unlock();
}

extern "C" void stop_roi(jlong _tls) {
  thread_mutex.lock();

  agent_group->stop();
  jvm_execution->stop();
  gc_threads->stop();
  agent_state->stop();

  write_stats();

  /* Restore prefetcher state */
  for (uint i = 0; i < agent_state->get_num_gc_cpu(); i++) {
    uint gc_cpu = agent_state->get_gc_cpu(i);
    enable_prefetcher(gc_cpu);
  }
  for (uint i = 0; i < agent_state->get_num_jvm_cpu(); i++) {
    uint jvm_cpu = agent_state->get_jvm_cpu(i);
    enable_prefetcher(jvm_cpu);
  }

  thread_mutex.unlock();
}

/*
 * Trigger: CounterThreadStart
 */
static void JNICALL thread_start(jvmtiEnv* jvmti_env, jlong thread_id,
                                 jboolean is_gc) {
  thread_mutex.lock();

  if (agent_state->is_finished() == true) {
    counter_warn("JVMTI: THREAD START IGNORED -> {}", thread_id);
  } else {
    counter_debug("JVMTI: THREAD START: {}", thread_id);
    if (is_gc == JNI_TRUE) {
      gc_threads->add_thread(thread_id, true, gc_counters);
    }
  }

  thread_mutex.unlock();
}

/*
 * Trigger: CounterThreadEnd
 */
static void JNICALL thread_end(jvmtiEnv* jvmti_env, jlong thread_id,
                               jboolean is_gc) {
  thread_mutex.lock();

  if (agent_state->is_finished() == true) {
    counter_warn("JVMTI: THREAD END IGNORED -> {}", thread_id);
  } else {
    counter_debug("JVMTI: THREAD END: {}", thread_id);
    if (is_gc == JNI_TRUE) {
      gc_threads->thread_end(thread_id);
    }
  }

  thread_mutex.unlock();
}
