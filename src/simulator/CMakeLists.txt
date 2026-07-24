list(APPEND CMAKE_PROGRAM_PATH ${JDKSIMULATORPATH}/bin)
find_package(Java 21 REQUIRED COMPONENTS Development)
include(UseJava)

set(DacapoChopinCallbackOutput "${CMAKE_CURRENT_BINARY_DIR}/DacapoChopinCallback.class")
set(DacapoChopinCallbackSource "${CMAKE_CURRENT_SOURCE_DIR}/DacapoChopinCallback.java")

add_custom_command(
    OUTPUT ${DacapoChopinCallbackOutput}
    COMMAND ${Java_JAVAC_EXECUTABLE} -cp ${DACAPOCHOPINJAR} -d ${CMAKE_CURRENT_BINARY_DIR} ${DacapoChopinCallbackSource}
    DEPENDS "${DacapoChopinCallbackSource}"
    COMMENT "Building Java class file for DacapoChopinCallback.java"
    VERBATIM
)
add_custom_target(Gem5_DacapoChopinCallback ALL DEPENDS ${DacapoChopinCallbackOutput})

add_library(dacapo_callback SHARED callback.cpp)
target_include_directories(dacapo_callback PRIVATE "include" "${JDKSIMULATORPATH}/include" "${JDKSIMULATORPATH}/include/linux")
set_target_properties(dacapo_callback PROPERTIES OUTPUT_NAME callback)
