#ifndef CALLBACK_H
#define CALLBACK_H

#include <dlfcn.h>
#include <jni.h>
#include <unistd.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>

/*
 * The start signal callback searches for the shared library toolkit, and then
 * executes its start_roi method.
 */
void start_signal();
void stop_signal();

/* Callbacks used by DaCapo harness. */
extern "C" JNIEXPORT void JNICALL
Java_DacapoChopinCallback_startSignal(JNIEnv*, jobject);
extern "C" JNIEXPORT void JNICALL Java_DacapoChopinCallback_stopSignal(JNIEnv*,
                                                                       jobject);

/* Callbacks used by Renaissance harness. */
extern "C" JNIEXPORT void JNICALL Java_RenaissancePlugin_startSignal(JNIEnv*,
                                                                     jobject);
extern "C" JNIEXPORT void JNICALL Java_RenaissancePlugin_stopSignal(JNIEnv*,
                                                                    jobject);

#endif  // CALLBACK_H
