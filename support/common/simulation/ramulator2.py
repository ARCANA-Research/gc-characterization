import os
import shutil

from typing import Dict, List

from common import check, utils
from common.simulation import (
    check_utils,
    counter_utils,
    gem5,
    sample_utils,
    simulation_utils,
)

RANK_COUNT = 2

START_STATISTIC_TOKEN = "BEGIN RAMULATOR2 STATS"
END_STATISTIC_TOKEN = "END RAMULATOR2 STATS"


def parse_trace(p_trace: str) -> List:
    l_phases = list()
    with utils.CommonFile(p_trace, "r") as f_log:
        for line in f_log:
            if "SWITCH JDK PHASE" in line:
                l_phases.append(int(line.split()[-1]))
    return l_phases


def setup_counters(y_counter: "yaml.YAMLObject", num_phases: int) -> List:
    num_phases = num_phases + 1  # extra output at the end
    l_counters = list()
    for counter in y_counter["ramulator2"]:
        l_multiplier = [None]
        if "multiplier" in counter:
            if counter["multiplier"] == "ranks":
                l_multiplier = [str(m) for m in range(RANK_COUNT)]
            else:
                assert False
        for mult in l_multiplier:
            l_counters += counter_utils.get_counter_list(counter, mult, num_phases)
    l_counters.append(
        counter_utils.StaticCounter(
            "jdk_execution_phase:", num_phases, "jdkphase", None
        )
    )
    return l_counters


def update_counter_values(
    l_counters: List, p_stats: str, num_phases: int, l_move: List
) -> List:
    l_counters = simulation_utils.parse_statistics(
        l_counters, p_stats, END_STATISTIC_TOKEN
    )
    # counter_utils.print_counter_list(l_counters)
    for counter in l_counters:
        counter.finished_adding_values()
        counter.fix_ramulator2()
        counter.drop_idx(0)
        counter.merge_gcstw(l_move)
        assert num_phases == len(counter)
    return l_counters


def generate_counters(
    y_counter: "yaml.YAMLObject",
    p_stats: str,
    num_phases: int,
    l_jdk_events: List,
) -> List:
    l_move, num_valid_phases, l_jdk_events = simulation_utils.generate_gcstw_move(
        l_jdk_events
    )
    l_counters = setup_counters(y_counter, num_phases)
    # counter_utils.print_counter_list(l_counters)
    l_counters = update_counter_values(l_counters, p_stats, num_valid_phases, l_move)
    # counter_utils.print_counter_list(l_counters)
    l_counters = simulation_utils.drop_disabled(l_counters, l_jdk_events)
    return l_counters


def check_ramulator2_execution(
    d_event_state: Dict,
    p_execution: str,
    p_eventmap: str,
    create_trace: bool,
    sample_execution: bool = False,
) -> Dict:
    p_simerr = f"{p_execution}/simerr.log"
    p_stats = f"{p_execution}/ramulator_stats.gz"
    if sample_execution == True:
        p_simerr = sample_utils.get_sample_path(p_simerr)
        p_stats = sample_utils.get_sample_path(p_stats)
    if os.path.isfile(p_simerr) == False:
        return d_event_state
    b_stats_found = os.path.isfile(p_stats)
    d_event_state["RAMUALTOR2_STATS_FOUND"] = check.Status.from_bool(b_stats_found)
    if b_stats_found == False:
        return d_event_state
    b_stats_valid = check_utils.check_if_log_valid(p_stats)
    d_event_state["RAMUALTOR2_STATS_FILE_VALID"] = check.Status.from_bool(b_stats_valid)
    if b_stats_valid == False:
        return d_event_state
    if create_trace == True:
        p_trace = f"{p_execution}/ramulator_trace.gz"
        if os.path.isfile(p_trace) == False:
            d_event_state["RAMUALTOR2_TRACE_FILE_VALID"] = check.Status.FAILED
        else:
            d_event_state["RAMUALTOR2_TRACE_FILE_VALID"] = check.Status.from_bool(
                check_utils.check_if_log_valid(p_trace)
            )
    else:
        d_event_state["RAMUALTOR2_TRACE_FILE_VALID"] = check.Status.DISREGARD
    if sample_execution == True:
        d_event_state["RAMUALTOR2_TRACE_FILE_VALID"] = check.Status.DISREGARD
    l_jdk_events = gem5.parse_simerr(p_simerr)
    l_ramulator2_stat_events = check_utils.get_jdk_phase_from_ramulator2_stats(
        p_execution, p_stats, l_jdk_events
    )
    if l_ramulator2_stat_events is None:
        return d_event_state
    ramulator2_phases_match = l_jdk_events == l_ramulator2_stat_events
    d_event_state["RAMULATOR2_STATS_PHASES_MATCH_SIMULATION"] = check.Status.from_bool(
        ramulator2_phases_match
    )
    return d_event_state
