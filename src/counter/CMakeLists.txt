list(APPEND CMAKE_PROGRAM_PATH ${JDKCOUNTERPATH}/bin)
find_package(Java 21 REQUIRED COMPONENTS Development)
include(UseJava)

add_library(Perf_callback SHARED callback.cpp)
target_include_directories(Perf_callback PRIVATE "${JDKCOUNTERPATH}/include" "${JDKCOUNTERPATH}/include/linux" "include")
set_target_properties(Perf_callback PROPERTIES OUTPUT_NAME callback)

set(DacapoChopinCallbackOutput "${CMAKE_CURRENT_BINARY_DIR}/DacapoChopinCallback.class")
set(DacapoChopinCallbackSource "${CMAKE_CURRENT_SOURCE_DIR}/DacapoChopinCallback.java")
add_custom_command(
    OUTPUT ${DacapoChopinCallbackOutput}
    COMMAND ${Java_JAVAC_EXECUTABLE} -cp ${DACAPOCHOPINJAR} -d ${CMAKE_CURRENT_BINARY_DIR} ${DacapoChopinCallbackSource}
    DEPENDS "${DacapoChopinCallbackSource}"
    COMMENT "Building Java class file for DacapoChopinCallback.java"
    VERBATIM
)
add_custom_target(Perf_DacapoChopinCallback ALL DEPENDS ${DacapoChopinCallbackOutput})

add_library(Perf_agent SHARED agent.cpp components/agent_counter.cpp components/agent_state.cpp components/base.cpp components/counter_data.cpp components/per_phase_counter_data.cpp)
target_include_directories(Perf_agent PRIVATE "${JDKCOUNTERPATH}/include" "${JDKCOUNTERPATH}/include/linux" "${CMAKE_CURRENT_SOURCE_DIR}/include" "${libpfm4_include_dir}" ${yaml-cpp_SOURCE_DIR}/include)
target_link_libraries(Perf_agent libpfm4 yaml-cpp spdlog)
set_target_properties(Perf_agent PROPERTIES OUTPUT_NAME agent)

add_library(Perf_concurrent SHARED concurrent.cpp components/agent_counter.cpp components/agent_state.cpp components/base.cpp components/counter_data.cpp components/per_phase_counter_data.cpp components/counter_thread.cpp components/counter_manager.cpp components/jvm_execution.cpp components/inherit_perf_counter.cpp components/thread_perf_counter.cpp)
target_include_directories(Perf_concurrent PRIVATE "${JDKCOUNTERPATH}/include" "${JDKCOUNTERPATH}/include/linux" "${CMAKE_CURRENT_SOURCE_DIR}/include" "${libpfm4_include_dir}" ${yaml-cpp_SOURCE_DIR}/include)
target_link_libraries(Perf_concurrent libpfm4 yaml-cpp spdlog)
target_compile_definitions(Perf_concurrent PRIVATE CONCURRENT_JVMTI)
set_target_properties(Perf_concurrent PROPERTIES OUTPUT_NAME concurrent)

add_library(Perf_no_prefetcher SHARED no_prefetcher.cpp components/agent_counter.cpp components/agent_state.cpp components/base.cpp components/counter_data.cpp components/per_phase_counter_data.cpp components/counter_thread.cpp components/counter_manager.cpp components/jvm_execution.cpp components/inherit_perf_counter.cpp components/thread_perf_counter.cpp components/msr_control.cpp)
target_include_directories(Perf_no_prefetcher PRIVATE "${JDKCOUNTERPATH}/include" "${JDKCOUNTERPATH}/include/linux" "${CMAKE_CURRENT_SOURCE_DIR}/include" "${libpfm4_include_dir}" ${yaml-cpp_SOURCE_DIR}/include)
target_link_libraries(Perf_no_prefetcher libpfm4 yaml-cpp spdlog)
target_compile_definitions(Perf_no_prefetcher PRIVATE CONCURRENT_JVMTI)
set_target_properties(Perf_no_prefetcher PROPERTIES OUTPUT_NAME no_prefetcher)

add_library(Perf_no_prefetcher_concurrent SHARED no_prefetcher_concurrent.cpp components/agent_counter.cpp components/agent_state.cpp components/base.cpp components/counter_data.cpp components/per_phase_counter_data.cpp components/counter_thread.cpp components/counter_manager.cpp components/jvm_execution.cpp components/inherit_perf_counter.cpp components/thread_perf_counter.cpp components/msr_control.cpp)
target_include_directories(Perf_no_prefetcher_concurrent PRIVATE "${JDKCOUNTERPATH}/include" "${JDKCOUNTERPATH}/include/linux" "${CMAKE_CURRENT_SOURCE_DIR}/include" "${libpfm4_include_dir}" ${yaml-cpp_SOURCE_DIR}/include)
target_link_libraries(Perf_no_prefetcher_concurrent libpfm4 yaml-cpp spdlog)
target_compile_definitions(Perf_no_prefetcher_concurrent PRIVATE CONCURRENT_JVMTI)
set_target_properties(Perf_no_prefetcher_concurrent PROPERTIES OUTPUT_NAME no_prefetcher_concurrent)

add_library(Perf_no_prefetcher_stw SHARED no_prefetcher_stw.cpp components/agent_counter.cpp components/agent_state.cpp components/base.cpp components/counter_data.cpp components/per_phase_counter_data.cpp components/counter_thread.cpp components/counter_manager.cpp components/jvm_execution.cpp components/inherit_perf_counter.cpp components/thread_perf_counter.cpp components/msr_control.cpp)
target_include_directories(Perf_no_prefetcher_stw PRIVATE "${JDKCOUNTERPATH}/include" "${JDKCOUNTERPATH}/include/linux" "${CMAKE_CURRENT_SOURCE_DIR}/include" "${libpfm4_include_dir}" ${yaml-cpp_SOURCE_DIR}/include)
target_link_libraries(Perf_no_prefetcher_stw libpfm4 yaml-cpp spdlog)
target_compile_definitions(Perf_no_prefetcher_stw PRIVATE CONCURRENT_JVMTI)
set_target_properties(Perf_no_prefetcher_stw PROPERTIES OUTPUT_NAME no_prefetcher_stw)

add_executable(Perf_verify verify.cpp components/base.cpp components/verify_thread.cpp)
target_include_directories(Perf_verify PRIVATE "${JDKCOUNTERPATH}/include" "${JDKCOUNTERPATH}/include/linux" "${CMAKE_CURRENT_SOURCE_DIR}/include" ${yaml-cpp_SOURCE_DIR}/include)
target_link_libraries(Perf_verify libpfm4 yaml-cpp spdlog)
set_target_properties(Perf_verify PROPERTIES OUTPUT_NAME verify)
