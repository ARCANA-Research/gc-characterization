#include <unistd.h>
#include <yaml-cpp/yaml.h>

#include <chrono>
#include <filesystem>
#include <map>
#include <string>
#include <thread>
#include <vector>

#include "base.h"
#include "spdlog/sinks/basic_file_sink.h"
#include "verify_thread.h"

/* Sleep between checking for new threads, and new CPUs executed. */
#define SLEEP_MILLISECONDS 50

std::map<tid_t, VerifyThread*> tid_map;

void process_tid(std::string tid_path, bool non_jvm_thread,
                 counter_t current_check_count) {
  tid_t tid = get_tid(tid_path);
  if (tid_map.find(tid) != tid_map.end()) {
    VerifyThread* verify_thread = tid_map.at(tid);
    counter_assert(verify_thread->is_alive(),
                   "VERIFY ({}): Dead thread is alive", tid);
    try {
      verify_thread->update();
    } catch (...) {
      spdlog::warn("VERIFT ({}): Failed to update thread status", tid);
    }
  } else {
    counter_debug("Starting: {}", tid);
    tid_map.insert({tid, new VerifyThread(tid, tid_path, current_check_count,
                                          non_jvm_thread)});
  }
}

void find_dead_tids(counter_t current_check_count) {
  for (auto const& tid_exec : tid_map) {
    VerifyThread* verify_thread = tid_exec.second;
    if (verify_thread->is_alive() == true) {
      if (verify_thread->get_last_check() != current_check_count) {
        verify_thread->kill();
        counter_debug("Ended: {}", tid_exec.first);
      }
    }
  }
}

bool get_tid_yaml(YAML::Node& verify_node, std::string config_path,
                  counter_t total_time) {
  YAML::Node config_node = YAML::LoadFile(config_path);
  std::vector<uint> jvm_cpus =
      config_node["counter"]["jvm-cpus"].as<std::vector<uint>>();
  std::vector<uint> gc_cpus =
      config_node["counter"]["gc-cpus"].as<std::vector<uint>>();
  bool all_pass = true;
  YAML::Node tid_map_node;
  uint i = 0;
  for (auto const& tid_exec : tid_map) {
    VerifyThread* verify_thread = tid_exec.second;
    tid_map_node[i] = verify_thread->to_yaml(&jvm_cpus, &gc_cpus, total_time);
    all_pass &= tid_map_node[i]["valid"].as<bool>();
    spdlog::info(verify_thread->to_string(tid_map_node[i]));
    i += 1;
  }
  verify_node["threads"] = tid_map_node;
  return all_pass;
}

bool get_cpu_yaml(YAML::Node& verify_node, std::string config_path) {
  YAML::Node config_node = YAML::LoadFile(config_path);
  bool all_pass = true;
  uint i = 0;
  uint num_cpus = config_node["counter"]["num-cpus"].as<uint>();
  std::string expected_governor =
      config_node["counter"]["cpu-governor"].as<std::string>();
  YAML::Node cpu_node;
  for (uint c = 0; c < num_cpus; c++) {
    YAML::Node governor_node;
    std::string governor = get_cpu_governor(c);
    int frequency = get_cpu_frequency(c);
    governor_node["cpu"] = c;
    governor_node["governor"] = governor;
    governor_node["frequency"] = frequency;
    bool governor_valid = expected_governor == governor;
    governor_node["valid"] = governor_valid;
    cpu_node[i] = governor_node;
    std::vector<std::string> cpu_vector = {
        convert_bool_to_string(governor_valid),
        pad_string(std::to_string(c), 2),
        governor,
        std::to_string(frequency),
    };
    spdlog::info(convert_iterable_to_string(cpu_vector.begin(),
                                            cpu_vector.end(), "", "", " | "));
    all_pass &= governor_valid;
    i += 1;
  }
  verify_node["cpus"] = cpu_node;
  return all_pass;
}

int main(int argc, char* argv[]) {
  counter_assert(argc == 4, "VERIFY: Invalid number of arguments passed {}",
                 argc);
  std::string log_base_path = argv[1];
  auto logger_file_sink = std::make_shared<spdlog::sinks::basic_file_sink_mt>(
      log_base_path + ".log", true);
  auto verify_logger =
      std::make_shared<spdlog::logger>("verify_logger", logger_file_sink);
#if DEBUG_LOG
  verify_logger->set_level(spdlog::level::debug);
#else
  verify_logger->set_level(spdlog::level::info);
#endif
  verify_logger->set_pattern("[%H:%M:%S.%e] [%^%l%$] %v");
  spdlog::set_default_logger(verify_logger);

  counter_debug("STARTED VERIFY");

  struct timespec curr_time;
  const uint64_t sec_to_ns = 1e9;
  counter_t current_check_count = 0;

  tid_t pid = std::stoi(argv[2]);
  std::string config_path = argv[3];
  spdlog::info("AGENT PID: {}", pid);

  tid_t self_pid = getpid();

  spdlog::info("VERIFY PID: {}", self_pid);

  clock_gettime(CLOCK_REALTIME, &curr_time);
  counter_t verify_start_time =
      curr_time.tv_sec * sec_to_ns + curr_time.tv_nsec;

  std::string task_path = "/proc/" + std::to_string(pid) + "/task/";
  while (std::filesystem::exists(task_path.c_str()) == true) {
    process_tid("/proc/" + std::to_string(self_pid), true, current_check_count);
    for (auto& p : std::filesystem::directory_iterator(task_path)) {
      process_tid(p.path().string(), false, current_check_count);
    }
    find_dead_tids(current_check_count);
    current_check_count += 1;
    std::this_thread::sleep_for(std::chrono::milliseconds(SLEEP_MILLISECONDS));
  }

  find_dead_tids(current_check_count);

  clock_gettime(CLOCK_REALTIME, &curr_time);
  counter_t verify_end_time = curr_time.tv_sec * sec_to_ns + curr_time.tv_nsec;

  YAML::Node verify_node;
  verify_node["agent_pid"] = pid;
  verify_node["verify_pid"] = self_pid;
  bool verify_pass = true;
  verify_pass &= get_tid_yaml(verify_node, config_path,
                              verify_end_time - verify_start_time);
  verify_pass &= get_cpu_yaml(verify_node, config_path);
  verify_node["passed"] = verify_pass;
  verify_node["clock"] = current_check_count;
  spdlog::info("CLOCK: {}", current_check_count);
  spdlog::info((verify_pass == true) ? "COUNTER: PASSED" : "COUNTER: FAILED");

  save_yaml_path(verify_node, log_base_path + ".yaml");

  counter_debug("ENDED VERIFY");

  return 0;
}
