#ifndef SIMULATOR_M5_H
#define SIMULATOR_M5_H

#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>

#include <cstdint>

inline void m5_exit() {
  __asm__ __volatile__(".word 0x040F; .word 0x0021;" : : "D"(0) :);
}

inline void m5_switchcpu() {
  __asm__ __volatile__(".word 0x040F; .word 0x0052;" : : :);
}

inline void m5_startroi() {
  __asm__ __volatile__(".word 0x040F; .word 0x005C;" : : :);
}

inline void m5_stoproi() {
  __asm__ __volatile__(".word 0x040F; .word 0x005D;" : : :);
}

inline void m5_gcevent(int eventid) {
  __asm__ __volatile__(".word 0x040F; .word 0x005E;" : : "D"(eventid) :);
}

inline void m5_gcthreadstart(int threadid) {
  __asm__ __volatile__(".word 0x040F; .word 0x005F;" : : "D"(threadid) :);
}

inline void m5_gcthreadend(int threadid) {
  __asm__ __volatile__(".word 0x040F; .word 0x0060;" : : "D"(threadid) :);
}

#endif  // SIMULATOR_M5_H
