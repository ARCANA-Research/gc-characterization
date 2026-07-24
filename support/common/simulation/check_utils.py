import os
import re

from datetime import datetime
from typing import Callable, Dict, List

from common import check, check_table, utils
from common.simulation import counter_utils, gem5, ramulator2, simulation_utils


def get_jdk_phase_from_gem5_stats(
    p_execution: str, p_stats: str, l_jdk_events: List
) -> List:
    try:
        d_gem5_phases = simulation_utils.parse_statistics(
            [
                counter_utils.StaticCounter(
                    "statJdkPhase", len(l_jdk_events) + 1, "jdkphase", None
                )
            ],
            p_stats,
            gem5.END_STATISTIC_TOKEN,
        )
        return d_gem5_phases[0].data[:-1]
    except Exception as e:
        print(
            f"PARSEERROR: Too few phases in simout for gem5 -> {str(e)} {p_execution}"
        )
        return None
    return None


def get_jdk_phase_from_ramulator2_stats(
    p_execution: str, p_stats: str, l_jdk_events: List
) -> List:
    try:
        d_ramulator2_phases = simulation_utils.parse_statistics(
            [
                counter_utils.StaticCounter(
                    "jdk_execution_phase:", len(l_jdk_events) + 1, "jdkphase", None
                )
            ],
            p_stats,
            ramulator2.END_STATISTIC_TOKEN,
        )
        return d_ramulator2_phases[0].data[1:]
    except Exception as e:
        print(
            f"PARSEERROR: Too few phases in simout for Ramulator2 -> {str(e)} {p_execution}"
        )
    return None


def generate_args(p_outdir: str) -> List:
    l_args = list()
    l_expected_executions = simulation_utils.generate_expected_execution_logs(p_outdir)
    for p_execution in l_expected_executions:
        l_args.append(
            {
                "outdir": p_outdir,
                "execution": p_execution,
            }
        )
    return l_args, l_expected_executions


def process_outdir(
    l_executions: List,
    p_outdir: str,
    p_status: str,
    framework: str,
    split_benchmark_path: Callable,
    check_sample: bool = True,
) -> None:
    d_benchmarks = simulation_utils.combine_check_dict(
        l_executions, framework, split_benchmark_path
    )
    d_benchmarks = check.check_all_executions(
        d_benchmarks,
        split_benchmark_path,
        simulation_utils.NUM_ITERATIONS,
    )
    config = utils.parse_yaml(f"{p_outdir}/config.yaml")
    if "gc" in config:
        l_gc = config["gc"]
    else:
        l_gc = None
    check.generate_check_file(
        p_outdir,
        d_benchmarks,
        split_benchmark_path,
        l_gc,
        False,
        check_sample,
    )
    table = check_table.generate_table(
        d_benchmarks,
        p_status,
        split_benchmark_path,
        True,
        simulation_utils.NUM_ITERATIONS,
    )
    utils.save_yaml(d_benchmarks, f"{p_outdir}/check_table.yaml")
    utils.write_to_file(table, f"{p_outdir}/check.ansi")


def check_if_log_valid(p_log: str) -> bool:
    with utils.CommonFile(p_log, "r") as f_log:
        try:
            num_lines = 0
            for line in f_log:
                num_lines += 1
        except Exception as e:
            return False
    return True


def check_condor_execution(d_event_state: Dict, p_execution: str) -> Dict:
    p_condor = f"{p_execution}/condor.log"
    b_condor_found = os.path.isfile(p_condor)
    if b_condor_found == False:
        d_event_state["CONDOR_FOUND"] = check.Status.DISREGARD
        d_event_state["NO_CONDOR_OOM"] = check.Status.DISREGARD
        d_event_state["NO_CONDOR_ABORTED"] = check.Status.DISREGARD
        d_event_state["NO_CONDOR_EVICTED"] = check.Status.DISREGARD
        d_event_state["CONDOR_STARTED"] = check.Status.DISREGARD
        d_event_state["CONDOR_TERMINATED"] = check.Status.DISREGARD
        return d_event_state
    d_event_state["CONDOR_FOUND"] = check.Status.from_bool(b_condor_found)
    query_bool = utils.check_file_has_strings(
        p_condor,
        [
            "cgroup memory limit",
            "was aborted",
            "was evicted",
            "Finished transferring input files",
            "Job terminated of its own accord at",
        ],
    )
    d_event_state["NO_CONDOR_OOM"] = check.Status.from_bool(not query_bool[0])
    d_event_state["NO_CONDOR_ABORTED"] = check.Status.from_bool(not query_bool[1])
    d_event_state["NO_CONDOR_EVICTED"] = check.Status.from_bool(not query_bool[2])
    d_event_state["CONDOR_STARTED"] = check.Status.from_bool(query_bool[3])
    d_event_state["CONDOR_TERMINATED"] = check.Status.from_bool(query_bool[4])
    init_time = None
    current_time = None
    current_memory = None
    regex_pattern = re.compile(
        r"[\d][\d][\d][\d]-[\d][\d]-[\d][\d] [\d][\d]:[\d][\d]:[\d][\d]"
    )
    time_format = "%Y-%m-%d %H:%M:%S"
    with utils.CommonFile(p_condor, "r") as f_condor:
        for log_line in f_condor:
            re_search = re.search(regex_pattern, log_line)
            if re_search is not None:
                time_string = re_search.group()
                parsed_time = datetime.strptime(time_string, time_format)
                if init_time is None:
                    init_time = parsed_time
                current_time = parsed_time
            else:
                if "MemoryUsage of job (MB)" in log_line:
                    current_memory = int(log_line.split()[0])
    executiom_time = current_time - init_time
    if current_memory is None:
        current_memory = 0
    d_event_state["EXEC_HOURS"] = round(executiom_time.total_seconds() / 3600, 1)
    d_event_state["MEM_GB"] = round(current_memory / 1024, 1)
    d_event_state["EXEC_PATH"] = p_execution
    return d_event_state
