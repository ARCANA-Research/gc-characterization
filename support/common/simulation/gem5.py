import os

from typing import Callable, Dict, List

from common import check, jvm, utils
from common.simulation import check_utils, counter_utils, sample_utils, simulation_utils


START_STATISTIC_TOKEN = "Begin Simulation Statistics"
END_STATISTIC_TOKEN = "End Simulation Statistics"


def parse_simerr(p_simerr: str) -> List:
    l_phases = list()
    with utils.CommonFile(p_simerr, "r") as f_log:
        for line in f_log:
            if "DUMP AND RESET STATS FOR PHASE" in line:
                l_phases.append(int(line.split()[-1]))
    return l_phases


def setup_counters(
    y_counter: "yaml.YAMLObject", config: "yaml.YAMLObject", num_phases: int
) -> List:
    num_phases = num_phases + 1  # extra output at the end
    l_counters = list()
    for counter in y_counter["gem5"]:
        l_multiplier = [None]
        if "multiplier" in counter:
            if counter["multiplier"] == "cores":
                l_multiplier = [
                    str(m) for m in range(config["hardware"]["cpu"]["cores"])
                ]
            else:
                assert False
        for mult in l_multiplier:
            l_counters += counter_utils.get_counter_list(counter, mult, num_phases)
    l_counters.append(
        counter_utils.StaticCounter("statJdkPhase", num_phases, "jdkphase", None)
    )
    return l_counters


def update_counter_values(
    l_counters: List, p_stats: str, num_phases: int, l_move: List
) -> List:
    l_counters = simulation_utils.parse_statistics(
        l_counters, p_stats, END_STATISTIC_TOKEN
    )
    for counter in l_counters:
        counter.finished_adding_values()
        counter.drop_idx(-1)
        counter.merge_gcstw(l_move)
        assert num_phases == len(counter)
    return l_counters


def generate_counters(
    y_counter: "yaml.YAMLObject",
    config: "yaml.YAMLObject",
    p_stats: str,
    num_phases: int,
    l_jdk_events: List,
) -> List:
    l_move, num_valid_phases, l_jdk_events = simulation_utils.generate_gcstw_move(
        l_jdk_events
    )
    l_counters = setup_counters(y_counter, config, num_phases)
    # counter_utils.print_counter_list(l_counters)
    l_counters = update_counter_values(l_counters, p_stats, num_valid_phases, l_move)
    # counter_utils.print_counter_list(l_counters)
    l_counters = simulation_utils.drop_disabled(l_counters, l_jdk_events)
    # counter_utils.print_counter_list(l_counters)
    return l_counters


def check_gem5_simout(d_event_state: Dict, p_execution: str) -> Dict:
    p_simout = f"{p_execution}/simout.log"
    start_time = None
    end_time = None
    if os.path.isfile(p_simout) == False:
        return d_event_state
    with utils.CommonFile(p_simout, "r") as f_simout:
        for log_line in f_simout:
            try:
                if "Start ROI" in log_line:
                    start_time = float(log_line.split()[0][1:-2])
                elif "Stop ROI" in log_line:
                    end_time = float(log_line.split()[0][1:-2])
                elif "Simulation End" in log_line and end_time is None:
                    end_time = float(log_line.split()[0][1:-2])
            except Exception as e:
                print(
                    f"PARSEERROR: Skipping simout analysis -> {str(e)} {log_line} {p_simout}"
                )
                return d_event_state
    if start_time is None:
        return d_event_state
    if end_time is None and (
        d_event_state["EXEC_HOURS"] != check.Status.UNKNOWN
        and d_event_state["EXEC_HOURS"] != check.Status.DISREGARD
    ):
        d_event_state["ROI_HOURS"] = round(
            float(d_event_state["EXEC_HOURS"]) - float(start_time / 3600), 1
        )
    else:
        d_event_state["ROI_HOURS"] = round((end_time - start_time) / 3600, 1)
    return d_event_state


def check_gem5_execution(
    d_event_state: Dict,
    p_execution: str,
    p_eventmap: str,
    split_benchmark_path: Callable,
) -> Dict:
    p_simerr = f"{p_execution}/simerr.log"
    b_simerr_found = os.path.isfile(p_simerr)
    d_event_state["SIMERR_FOUND"] = check.Status.from_bool(b_simerr_found)
    if b_simerr_found == False:
        return d_event_state
    query_bool = utils.check_file_has_strings(
        p_simerr,
        [
            "panic: Possible Deadlock detected",
            "BEGIN LIBC BACKTRACE",
            "segmentation fault",
        ],
    )
    no_ruby_deadlock = not query_bool[0]
    no_gem5_error = not query_bool[1]
    no_segmentation_fault = not query_bool[2]
    d_event_state["NO_RUBY_DEADLOCK"] = check.Status.from_bool(no_ruby_deadlock)
    d_event_state["NO_GEM5_ERROR"] = check.Status.from_bool(no_gem5_error)
    d_event_state["NO_SEGMENTATION_FAULT"] = check.Status.from_bool(
        no_segmentation_fault
    )
    if no_ruby_deadlock == False or no_gem5_error == False:
        d_event_state["GEM5_STATS_FOUND"] = check.Status.DISREGARD
        d_event_state["GEM5_STATS_PHASES_MATCH_SIMULATION"] = check.Status.DISREGARD
        d_event_state["GEM5_STATS_VALID_EVENTS"] = check.Status.DISREGARD
        return d_event_state
    return check_gem5_statistics(
        d_event_state, p_execution, p_eventmap, split_benchmark_path
    )


def check_gem5_statistics(
    d_event_state: Dict,
    p_execution: str,
    p_eventmap: str,
    split_benchmark_path: Callable,
    sample_execution: bool = False,
) -> Dict:
    p_simerr = f"{p_execution}/simerr.log"
    p_stats = f"{p_execution}/stats.gz"
    if sample_execution == True:
        p_simerr = sample_utils.get_sample_path(p_simerr)
        p_stats = sample_utils.get_sample_path(p_stats)
    b_stats_found = os.path.isfile(p_stats)
    d_event_state["GEM5_STATS_FOUND"] = check.Status.from_bool(b_stats_found)
    if b_stats_found == False:
        return d_event_state
    b_stats_valid = check_utils.check_if_log_valid(p_stats)
    d_event_state["GEM5_STATS_FILE_VALID"] = check.Status.from_bool(b_stats_valid)
    if b_stats_valid == False:
        return d_event_state
    l_jdk_events = parse_simerr(p_simerr)
    l_gem5_stat_events = check_utils.get_jdk_phase_from_gem5_stats(
        p_execution, p_stats, l_jdk_events
    )
    if l_gem5_stat_events is None:
        return d_event_state
    gem5_phases_match = l_jdk_events == l_gem5_stat_events
    d_event_state["GEM5_STATS_PHASES_MATCH_SIMULATION"] = check.Status.from_bool(
        gem5_phases_match
    )
    if p_eventmap is None:
        d_event_state["GEM5_STATS_VALID_EVENTS"] = check.Status.DISREGARD
    else:
        _, gc, _, _ = split_benchmark_path(p_execution)
        d_event_state["GEM5_STATS_VALID_EVENTS"] = check.Status.from_bool(
            check_if_valid_events(p_eventmap, l_jdk_events, gc)
        )
    return d_event_state


def check_if_valid_events(p_eventmap: str, l_jdk_events: List, gc: str) -> bool:
    l_gc_events, _, _ = jvm.valid_phases(p_eventmap, gc, True, True)
    for jdk_event in l_jdk_events:
        if jdk_event not in l_gc_events:
            return False
    return True
