#include "callback.h"

#include "common.h"

/*
 * The start signal callback searches for the shared library toolkit, and then
 * executes its start_roi method.
 */
void start_signal() {
  void (*start_roi)() = (void (*)())dlsym(dlopen(NULL, RTLD_LAZY), "start_roi");
  counter_assert(start_roi != NULL, "CALLBACK: Start ROI not found");
  counter_debug("ROI START");
  (*start_roi)();
  counter_debug("ROI START END");
}

/*
 * The stop signal callback searches for the shared library toolkit, and then
 * executes its stop_roi method.
 */
void stop_signal() {
  void (*stop_roi)() = (void (*)())dlsym(dlopen(NULL, RTLD_LAZY), "stop_roi");
  counter_assert(stop_roi != NULL, "CALLBACK: Stop ROI not found");
  counter_debug("ROI STOP");
  (*stop_roi)();
  counter_debug("ROI STOP END");
}

/*
 * DaCapo start
 */
extern "C" JNIEXPORT void JNICALL
Java_DacapoChopinCallback_startSignal(JNIEnv* env, jobject o) {
  start_signal();
}

/*
 * DaCapo stop
 */
extern "C" JNIEXPORT void JNICALL
Java_DacapoChopinCallback_stopSignal(JNIEnv* env, jobject o) {
  stop_signal();
}

/*
 * Renaissance start
 */
extern "C" JNIEXPORT void JNICALL
Java_RenaissancePlugin_startSignal(JNIEnv* env, jobject o) {
  start_signal();
}

/*
 * Renaissance stop
 */
extern "C" JNIEXPORT void JNICALL Java_RenaissancePlugin_stopSignal(JNIEnv* env,
                                                                    jobject o) {
  stop_signal();
}
