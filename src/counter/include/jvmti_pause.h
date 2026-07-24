#ifndef JVMTI_PAUSE_H
#define JVMTI_PAUSE_H

#include <cstring>

#include "base.h"

/* ============================= JVMTI CALLBACKS ============================ */
/*
 * All of the functions below are called by JVMTI as needed.
 */

#if USE_COUNTER_GC_EVENTS

static void JNICALL gc_event(jvmtiEnv* jvmti_env, jint event_id);

#else

static void JNICALL gc_start(jvmtiEnv* jvmti_env);
static void JNICALL gc_stop(jvmtiEnv* jvmti_env);

#endif

/* =============================== JVMTI SETUP ============================== */

JNIEXPORT jint JNICALL Agent_OnLoad(JavaVM* jvm, char* opts, void* reserved) {
  jvmtiEnv* jvmti;
  jvmtiError error;

  jint r = jvm->GetEnv((void**)&jvmti, JVMTI_VERSION_1_0);
  counter_assert(r == JNI_OK, "JVMTI: Could not intiailize JVMTI environment");

  jvmtiCapabilities jvm_capabilities;
  std::memset(&jvm_capabilities, 0, sizeof(jvmtiCapabilities));

#if USE_COUNTER_GC_EVENTS

  jvm_capabilities.can_generate_counter_events = 1;

#else

  jvm_capabilities.can_generate_garbage_collection_events = 1;

#endif

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

  return JNI_OK;
}

#if USE_COUNTER_GC_EVENTS

/*
 * Trigger: CounterGcEvent
 */
static void JNICALL gc_event(jvmtiEnv* jvmti_env, jint event_id) {
  counter_debug("JVMTI: GC EVENT: {}", event_id);
  execution_change_phase(event_id);
}

#else

/*
 * Trigger: GarbageCollectionStart
 */
static void JNICALL gc_start(jvmtiEnv* jvmti_env) {
  counter_debug("JVMTI: STW BEGIN");
  execution_change_phase(GC_STW_PHASE);
}

/*
 * Trigger: GarbageCollectionFinish
 */
static void JNICALL gc_stop(jvmtiEnv* jvmti_env) {
  counter_debug("JVMTI: STW END");
  execution_change_phase(MUTATOR_PHASE);
}

#endif

#endif  // JVMTI_PAUSE_H
