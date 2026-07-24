
#include "verify_thread.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <string>

#include "base.h"

VerifyThread::VerifyThread(tid_t tid, std::string tid_path,
                           counter_t current_check_count, bool non_jvm_thread)
    : tid(tid),
      tid_path(tid_path),
      alive(true),
      last_check(current_check_count),
      non_jvm_thread(non_jvm_thread) {
  try {
    name = get_tid_name(tid_path, true);
    set_cpu_mask();
    thread_setup = true;
  } catch (...) {
    spdlog::warn("VERIFT ({}): Thread end before setup", tid);
    name = "UNKNOWN";
    thread_setup = false;
  }
  clock_gettime(CLOCK_REALTIME, &curr_time);
  thread_start_time = curr_time.tv_sec * sec_to_ns + curr_time.tv_nsec;
}

void VerifyThread::set_cpu_mask() {
  std::string tid_status = tid_path + "/status";
  FILE* f = fopen(tid_status.c_str(), "r");
  if (!f) {
    counter_test(f, "VERIFY ({}): Could not open tid status file ({})", tid,
                 strerror(errno));
  }
  while (fgets(buf, VERIFY_CHAR_BUFFER_SIZE, f)) {
    if (std::strncmp(buf, "Cpus_allowed_list", 17) == 0) {
      std::string cpu_mask_str(buf + 19);
      std::stringstream cpu_list_string(cpu_mask_str);
      std::string cpu;
      while (std::getline(cpu_list_string, cpu, ',')) {
        cpu_mask.push_back(std::stoi(cpu));
      }
      /*
      while (std::getline(cpu_list_string, cpu, ',')) {
        if (cpu.find("-") != std::string::npos) {
          std::stringstream cpu_stream(cpu);
          std::string cpu_tmp;
          std::vector<int> cpu_list;
          while (std::getline(cpu_stream, cpu_tmp, '-')) {
            cpu_list.push_back(std::stoi(cpu_tmp));
          }
          int cpu_min = cpu_list[0];
          int cpu_max = cpu_list[1];
          for (int i = cpu_min; i < cpu_max + 1; i++) {
            cpu_mask.push_back(i);
          }
        } else {
          cpu_mask.push_back(std::stoi(cpu));
        }
      }
      */
      fclose(f);
      return;
    }
  }
  fclose(f);
  counter_test(false, "VERIFY ({}): No CPU mask found", tid);
}

void VerifyThread::update() {
  last_check += 1;
  std::string tid_stat = tid_path + "/stat";
  if (std::filesystem::exists(tid_stat.c_str()) == false) {
    return;
  }
  FILE* f = fopen(tid_stat.c_str(), "r");
  if (!f) {
    counter_test(f, "VERIFY ({}): Could not open tid stat file ({})", tid,
                 strerror(errno));
  }
  counter_test(fgets(buf, VERIFY_CHAR_BUFFER_SIZE, f),
               "VERIFY ({}): Could not read tid stat file", tid);
  std::istringstream cpu_list_string(buf);
  std::string column;
  uint column_idx = 0;
  std::string process_name;
  bool passed_process_name = false;
  bool reading_process_name = false;
  while (std::getline(cpu_list_string, column, ' ')) {
    if (passed_process_name == false) {
      if (reading_process_name == false) {
        if (column.find('(') != std::string::npos) {
          process_name += column;
          reading_process_name = true;
        }
      } else {
        process_name += column;
      }
      if (column.find(')') != std::string::npos) {
        name = process_name.substr(1, process_name.length() - 2);
        reading_process_name = false;
        passed_process_name = true;
      }
    } else {
      column_idx += 1;
      if (column_idx == LAST_EXECUTED_COLUMN_AFTER_NAME) {
        cpus_executed.insert(std::stoi(column));
        fclose(f);
        return;
      } else if (column_idx == STATUS_COLUMN_AFTER_NAME) {
        if (column == "R") {
          running_count += 1;
        } else if (column == "S" || column == "D") {
          sleeping_count += 1;
        }
      }
    }
  }
  fclose(f);
  counter_test(false, "VERIFY ({}): No last executed CPU found", tid);
}

void VerifyThread::kill() {
  alive = false;
  clock_gettime(CLOCK_REALTIME, &curr_time);
  thread_end_time = curr_time.tv_sec * sec_to_ns + curr_time.tv_nsec;
}

bool VerifyThread::is_alive() { return alive; }

counter_t VerifyThread::get_last_check() { return last_check; }

bool VerifyThread::check_if_cpu_mask_has_no_overlap(
    std::vector<uint>* expected_cpu_mask) {
  for (uint i = 0; i < expected_cpu_mask->size(); i++) {
    if (std::find(cpu_mask.begin(), cpu_mask.end(), (*expected_cpu_mask)[i]) !=
        cpu_mask.end()) {
      return false;
    }
  }
  return true;
}

bool VerifyThread::check_if_cpu_mask_equal(
    std::vector<uint>* expected_cpu_mask) {
  if (expected_cpu_mask->size() != cpu_mask.size()) {
    return false;
  }
  for (uint i = 0; i < cpu_mask.size(); i++) {
    if (cpu_mask[i] != (*expected_cpu_mask)[i]) {
      return false;
    }
  }
  return true;
}

bool VerifyThread::check_if_execution_cpus_in_mask() {
  for (uint cpu : cpus_executed) {
    if (std::find(cpu_mask.begin(), cpu_mask.end(), cpu) == cpu_mask.end()) {
      return false;
    }
  }
  return true;
}

bool VerifyThread::check_if_valid_execution(std::vector<uint>* jvm_cpus,
                                            std::vector<uint>* gc_cpus) {
  if (thread_setup == false) {
    return true;
  }
  bool valid_execution = check_if_execution_cpus_in_mask();
  if (non_jvm_thread == true) {
    return valid_execution && check_if_cpu_mask_has_no_overlap(jvm_cpus) &&
           check_if_cpu_mask_has_no_overlap(gc_cpus);
  }
  bool is_gc = is_gc_tid(name);
  if (is_gc) {
    return valid_execution && check_if_cpu_mask_equal(gc_cpus);
  }
  return valid_execution && check_if_cpu_mask_equal(jvm_cpus);
}

int VerifyThread::get_execution_percent(counter_t total_time) {
  counter_t thread_execution_time = thread_end_time - thread_start_time;
  return std::round((thread_execution_time * 100) / total_time);
}

std::string VerifyThread::to_string(YAML::Node tid_node) {
  std::vector<std::string> tid_string_vector;
  tid_string_vector.push_back(
      convert_bool_to_string(tid_node["valid"].as<bool>()));
  tid_string_vector.push_back(tid_node["tid"].as<std::string>());
  tid_string_vector.push_back(
      pad_string(tid_node["type"].as<std::string>(), 5));
  tid_string_vector.push_back(
      pad_string(tid_node["name"].as<std::string>(), 15));
  tid_string_vector.push_back(
      pad_string(tid_node["time"].as<std::string>(), 3));
  tid_string_vector.push_back(
      pad_string(tid_node["running_count"].as<std::string>(), 10));
  tid_string_vector.push_back(
      pad_string(tid_node["sleeping_count"].as<std::string>(), 10));
  tid_string_vector.push_back(pad_string(
      "CPU mask: " + convert_iterable_to_string(cpu_mask.begin(),
                                                cpu_mask.end(), "[", "]", ", "),
      101));
  tid_string_vector.push_back("Executed: " +
                              convert_iterable_to_string(cpus_executed.begin(),
                                                         cpus_executed.end(),
                                                         "[", "]", ", "));
  return convert_iterable_to_string(tid_string_vector.begin(),
                                    tid_string_vector.end(), "", "", " | ");
}

YAML::Node VerifyThread::to_yaml(std::vector<uint>* jvm_cpus,
                                 std::vector<uint>* gc_cpus,
                                 counter_t total_time) {
  if (name[name.length() - 1] == '\n') {
    name.erase(name.length() - 1);
  }
  YAML::Node node;
  node["tid"] = tid;
  node["name"] = name;
  bool is_gc = is_gc_tid(name);
  node["gc"] = is_gc;
  node["running_count"] = running_count;
  node["sleeping_count"] = sleeping_count;
  node["valid"] = check_if_valid_execution(jvm_cpus, gc_cpus);
  if (thread_setup == false) {
    node["type"] = "NA";
  } else if (non_jvm_thread == true) {
    node["type"] = "OTHER";
  } else {
    node["type"] = (is_gc == true) ? "GC" : "JVM";
  }
  node["time"] = std::to_string(get_execution_percent(total_time)) + "%";
  node["cpu_mask"] = convert_iterable_to_yaml(cpu_mask.begin(), cpu_mask.end());
  node["execution_cpu"] =
      convert_iterable_to_yaml(cpus_executed.begin(), cpus_executed.end());
  return node;
}

std::string convert_bool_to_string(bool flag) {
  return (flag == true) ? "PASSED" : "FAILED";
}

/* Pad strings that makes them look nicer when printing */
std::string pad_string(std::string original, uint expected_length) {
  if (original.length() < expected_length) {
    original += std::string(expected_length - original.length(), ' ');
  }
  return original;
}

std::string get_cpu_governor(uint cpu_id) {
  std::string cpu_governor_path = "/sys/devices/system/cpu/cpu" +
                                  std::to_string(cpu_id) +
                                  "/cpufreq/scaling_governor";
  FILE* f = fopen(cpu_governor_path.c_str(), "r");
  if (!f) {
    counter_assert(f, "VERIFY ({}): Could not open cpu governor file ({})",
                   cpu_id, strerror(errno));
  }
  char buf[VERIFY_CHAR_BUFFER_SIZE];
  counter_assert(fgets(buf, VERIFY_CHAR_BUFFER_SIZE, f),
                 "VERIFY ({}): Could not read cpu governor file", cpu_id);
  std::string governor_string = std::string(buf);
  if (governor_string[governor_string.length() - 1] == '\n') {
    governor_string.erase(governor_string.length() - 1);
  }
  fclose(f);
  return governor_string;
}

int get_cpu_frequency(uint cpu_id) {
  std::string cpu_frequency_path = "/sys/devices/system/cpu/cpu" +
                                   std::to_string(cpu_id) +
                                   "/cpufreq/scaling_cur_freq";
  FILE* f = fopen(cpu_frequency_path.c_str(), "r");
  if (!f) {
    counter_assert(f, "VERIFY ({}): Could not open cpu frequency file ({})",
                   cpu_id, strerror(errno));
  }
  char buf[VERIFY_CHAR_BUFFER_SIZE];
  counter_assert(fgets(buf, VERIFY_CHAR_BUFFER_SIZE, f),
                 "VERIFY ({}): Could not read cpu frequency file", cpu_id);
  std::string cpu_frequency = std::string(buf);
  if (cpu_frequency[cpu_frequency.length() - 1] == '\n') {
    cpu_frequency.erase(cpu_frequency.length() - 1);
  }
  fclose(f);
  return std::stoi(cpu_frequency);
}
