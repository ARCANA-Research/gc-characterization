#ifndef JVMTI_CONCURRENT_H
#define JVMTI_CONCURRENT_H

#include <cstring>

#include "base.h"
#include "common.h"

/* ============================ GLOBAL VARIABLES ============================ */

std::mutex thread_mutex;

/* ============================= JVMTI CALLBACKS ============================ */

#if USE_COUNTER_GC_EVENTS

static void JNICALL gc_event(jvmtiEnv* jvmti_env, jint event_id);

#else

static void JNICALL gc_start(jvmtiEnv* jvmti_env);
static void JNICALL gc_stop(jvmtiEnv* jvmti_env);

#endif

static void JNICALL thread_start(jvmtiEnv* jvmti_env, jlong thread_id,
                                 jboolean is_gc);
static void JNICALL thread_end(jvmtiEnv* jvmti_env, jlong thread_id,
                               jboolean is_gc);
static void JNICALL vm_start(jvmtiEnv* jvmti_env, JNIEnv* jni_env);

/* =============================== JVMTI SETUP ============================== */

JNIEXPORT jint JNICALL Agent_OnLoad(JavaVM* jvm, char* opts, void* reserved) {
  thread_mutex.lock();

  jvmtiEnv* jvmti;
  jvmtiError error;

  jint r = jvm->GetEnv((void**)&jvmti, JVMTI_VERSION_1_0);
  counter_assert(r == JNI_OK, "JVMTI: Could not intiailize JVMTI environment");

  jvmtiCapabilities jvm_capabilities;
  std::memset(&jvm_capabilities, 0, sizeof(jvmtiCapabilities));

#if !USE_COUNTER_GC_EVENTS

  jvm_capabilities.can_generate_garbage_collection_events = 1;

#endif

  jvm_capabilities.can_generate_counter_events = 1;

  error = jvmti->AddCapabilities(&jvm_capabilities);
  counter_assert(error == JVMTI_ERROR_NONE,
                 "JVMTI: Cannot add JVMTI GC capability");

  jvmtiEventCallbacks jvm_callbacks;
  std::memset(&jvm_callbacks, 0, sizeof(jvmtiEventCallbacks));

#if USE_COUNTER_GC_EVENTS

  jvm_callbacks.CounterGcEvent = &gc_event;

#else

  jvm_callbacks.GarbageCollectionStart = &gc_start;
  jvm_callbacks.GarbageCollectionFinish = &gc_stop;

#endif

  jvm_callbacks.CounterThreadStart = &thread_start;
  jvm_callbacks.CounterThreadEnd = &thread_end;
  jvm_callbacks.VMStart = &vm_start;

  error = jvmti->SetEventCallbacks(&jvm_callbacks, (jint)sizeof(jvm_callbacks));
  counter_assert(error == JVMTI_ERROR_NONE, "JVMTI: Cannot add JVMTI callback");

#if USE_COUNTER_GC_EVENTS

  error = jvmti->SetEventNotificationMode(
      JVMTI_ENABLE, JVMTI_EVENT_COUNTER_GC_EVENT, (jthread)NULL);
  counter_assert(error == JVMTI_ERROR_NONE,
                 "JVMTI: Cannot set GC Event notification");

#else

  error = jvmti->SetEventNotificationMode(
      JVMTI_ENABLE, JVMTI_EVENT_GARBAGE_COLLECTION_START, (jthread)NULL);
  counter_assert(error == JVMTI_ERROR_NONE,
                 "JVMTI: Cannot set GarbageCollectionStart notification");

  error = jvmti->SetEventNotificationMode(
      JVMTI_ENABLE, JVMTI_EVENT_GARBAGE_COLLECTION_FINISH, (jthread)NULL);
  counter_assert(error == JVMTI_ERROR_NONE,
                 "JVMTI: Cannot set GarbageCollectionFinish notification");

#endif

  error = jvmti->SetEventNotificationMode(
      JVMTI_ENABLE, JVMTI_EVENT_COUNTER_THREAD_START, (jthread)NULL);
  counter_assert(error == JVMTI_ERROR_NONE,
                 "JVMTI: Cannot set Counter ThreadStart notification");

  error = jvmti->SetEventNotificationMode(
      JVMTI_ENABLE, JVMTI_EVENT_COUNTER_THREAD_END, (jthread)NULL);
  counter_assert(error == JVMTI_ERROR_NONE,
                 "JVMTI: Cannot set Counter ThreadEnd notification");

  error = jvmti->SetEventNotificationMode(JVMTI_ENABLE, JVMTI_EVENT_VM_START,
                                          (jthread)NULL);
  counter_assert(error == JVMTI_ERROR_NONE,
                 "JVMTI: Cannot set JVM VMStart notification");

  thread_mutex.unlock();

  return JNI_OK;
}

#if USE_COUNTER_GC_EVENTS

/*
 * Trigger: CounterGcEvent
 */
static void JNICALL gc_event(jvmtiEnv* jvmti_env, jint event_id) {
  thread_mutex.lock();

  counter_debug("JVMTI: GC EVENT: {}", event_id);
  execution_change_phase(event_id);

  thread_mutex.unlock();
}

#else

/*
 * Trigger: GarbageCollectionStart
 */
static void JNICALL gc_start(jvmtiEnv* jvmti_env) {
  thread_mutex.lock();

  counter_debug("JVMTI: STW BEGIN");
  execution_change_phase(GC_STW_PHASE);

  thread_mutex.unlock();
}

/*
 * Trigger: GarbageCollectionFinish
 */
static void JNICALL gc_stop(jvmtiEnv* jvmti_env) {
  thread_mutex.lock();

  counter_debug("JVMTI: STW END");
  execution_change_phase(MUTATOR_PHASE);

  thread_mutex.unlock();
}

#endif

/*
 * Trigger: VMStart
 */
static void JNICALL vm_start(jvmtiEnv* jvmti_env, JNIEnv* jni_env) {
  // thread_mutex.lock();

  counter_debug("JVMTI: VM START");
  for (auto& p : std::filesystem::directory_iterator("/proc/self/task/")) {
    std::string tid_path = p.path().string();
    tid_t tid = get_tid(tid_path);
    std::string tid_name = get_tid_name(tid_path);
    bool tid_is_gc = is_gc_tid(tid_name);
    thread_start(jvmti_env, tid, (tid_is_gc == true) ? JNI_TRUE : JNI_FALSE);
  }

  // thread_mutex.unlock();
}

#endif  // JVMTI_CONCURRENT_H
