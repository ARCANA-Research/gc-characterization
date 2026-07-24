#include <jni.h>

#include "simulator.hpp"

extern "C" JNIEXPORT void JNICALL
Java_DacapoChopinCallback_startBenchmark(JNIEnv* env, jobject o) {
  m5_exit();
  m5_switchcpu();
  m5_exit();
  m5_startroi();
}

extern "C" JNIEXPORT void JNICALL
Java_DacapoChopinCallback_stopBenchmark(JNIEnv* env, jobject o) {
  m5_stoproi();
}
