#ifndef COMMON_H
#define COMMON_H

#if CONCURRENT_JVMTI

#include <mutex>

#endif

#include <sstream>
#include <stdexcept>
#include <string>

#include "spdlog/spdlog.h"

#ifndef DEBUG_LOG
#define DEBUG_LOG 0
#endif

#ifndef CONCURRENT_JVMTI
#define CONCURRENT_JVMTI 0
#endif

#ifndef USE_COUNTER_GC_EVENTS
#define USE_COUNTER_GC_EVENTS 0
#endif

/* ============================== CUSTOM TYPES ============================== */

using tid_t = uint32_t;
using counter_t = uint64_t;
using phase_t = uint;

/* ============================ GLOBAL VARIABLES ============================ */

#if CONCURRENT_JVMTI

/* Mutex to prevent race conditions. */
extern std::mutex thread_mutex;

#endif

/* ============================= HELPER METHODS ============================= */

/*
 * Shared assertion framework used in the toolkit. The concurernt implementation
 * releases the lock held by the shared library to make sure JVM finishes.
 */
template <typename... Args>
void counter_assert(bool condition, std::string fmt_string, Args&&... args) {
  if (!condition) {
    std::string output_string = "ASSERT FAILED: " + fmt_string;
#if (__GLIBC__ == 2 && __GLIBC_MINOR__ >= 39)
    spdlog::error(fmt::runtime(output_string), std::forward<Args>(args)...);
#else
    spdlog::error(output_string, std::forward<Args>(args)...);
#endif
#if CONCURRENT_JVMTI
    thread_mutex.unlock();
#endif
    exit(1);
  }
}

/*
 * Shared assertion framework used in the toolkit, which throws error instead
 * of exiting.
 */
template <typename... Args>
void counter_test(bool condition, std::string fmt_string, Args&&... args) {
  if (!condition) {
    std::string output_string = "ASSERT FAILED: " + fmt_string;
#if (__GLIBC__ == 2 && __GLIBC_MINOR__ >= 39)
    spdlog::error(fmt::runtime(output_string), std::forward<Args>(args)...);
#else
    spdlog::error(output_string, std::forward<Args>(args)...);
#endif
#if CONCURRENT_JVMTI
    thread_mutex.unlock();
#endif
    throw std::runtime_error("ASSERT FAILED");
  }
}

/* Debug log that is disabled normally */
template <typename... Args>
void counter_debug(std::string fmt_string, Args&&... args) {
#if DEBUG_LOG
#if (__GLIBC__ == 2 && __GLIBC_MINOR__ >= 39)
  spdlog::info(fmt::runtime(fmt_string), std::forward<Args>(args)...);
#else
  spdlog::info(fmt_string, std::forward<Args>(args)...);
#endif
#endif
}

/* Debug log that is disabled normally */
template <typename... Args>
void counter_warn(std::string fmt_string, Args&&... args) {
#if (__GLIBC__ == 2 && __GLIBC_MINOR__ >= 39)
  spdlog::warn(fmt::runtime(fmt_string), std::forward<Args>(args)...);
#else
  spdlog::warn(fmt_string, std::forward<Args>(args)...);
#endif
}

#endif  // COMMON_H
