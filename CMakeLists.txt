cmake_minimum_required(VERSION 3.20)
project(GC_Characterization VERSION 1.0 LANGUAGES CXX)

include(FetchContent)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE TRUE)
set(FETCHCONTENT_UPDATES_DISCONNECTED ON CACHE BOOL "Disable remote updates")

message(CHECK_START "Fetch libpfm4")
FetchContent_Declare(libpfm4_repo
  GIT_REPOSITORY https://github.com/wcohen/libpfm4.git
  GIT_TAG        91970fe6eb4e80b63f77fb54a9592e28a207050c
  GIT_SHALLOW    OFF
  SOURCE_DIR     ${CMAKE_SOURCE_DIR}/ext/libpfm4
)
FetchContent_MakeAvailable(libpfm4_repo)

message(CHECK_START "Fetch yaml-cpp")
FetchContent_Declare(yaml-cpp
  GIT_REPOSITORY https://github.com/jbeder/yaml-cpp.git
  GIT_TAG        0.8.0
  SOURCE_DIR     ${CMAKE_SOURCE_DIR}/ext/yaml-cpp
)
FetchContent_MakeAvailable(yaml-cpp)

message(CHECK_START "Fetch spdlog")
FetchContent_Declare(spdlog
  GIT_REPOSITORY https://github.com/gabime/spdlog.git
  GIT_TAG        v1.11.0
  SOURCE_DIR     ${CMAKE_SOURCE_DIR}/ext/spdlog
)
FetchContent_MakeAvailable(spdlog)
include_directories(${spdlog_SOURCE_DIR}/include)

set(libpfm4_output      "${libpfm4_repo_SOURCE_DIR}/lib/libpfm.so")
set(libpfm4_include_dir "${libpfm4_repo_SOURCE_DIR}/include")
add_custom_command(
  OUTPUT            "${libpfm4_output}"
  COMMAND           make -j$(nproc)
  DEPENDS           ${libpfm4_repo_SOURCE_DIR}
  WORKING_DIRECTORY ${libpfm4_repo_SOURCE_DIR}
  COMMENT           "Building libpfm4..."
  VERBATIM
)
add_custom_target(libpfm4_target ALL DEPENDS ${libpfm4_output})
add_library(libpfm4 SHARED IMPORTED GLOBAL)
add_dependencies(libpfm4 libpfm4_target)
set_target_properties(libpfm4
  PROPERTIES
  IMPORTED_LOCATION             "${libpfm4_output}"
  INTERFACE_INCLUDE_DIRECTORIES "${libpfm4_include_dir}"
)

set(DACAPOCHOPINJAR "${CMAKE_SOURCE_DIR}/deps/dacapo-23.11-MR2-chopin.jar")

set(JDKVERSION 21)
set(JDKCOUNTERPATH "${CMAKE_SOURCE_DIR}/deps/jdk21u-counter/build/linux-x86_64-server-release/images/jdk")
set(JDKSIMULATORPATH "${CMAKE_SOURCE_DIR}/deps/jdk21u-simulator/build/linux-x86_64-client-release/images/jdk")

add_subdirectory(src)
