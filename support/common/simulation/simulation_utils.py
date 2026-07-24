import copy
import os

from datetime import datetime
from enum import Enum
from typing import Dict, List, Callable

from common import check, combine, jvm, utils
from common.simulation import counter_utils, parse_utils

NUM_ITERATIONS = 1
NUM_MAX_ATTEMPTS = 1

AGENT_COUNTERS = ["GC_THREAD_COUNT", "GC_CPU_PERCENT"]


def merge_gc_simulation_pauses(
    phases_counter: "StaticCounter", l_values: List
) -> ["StaticCounter", List]:
    assert len(l_values) == len(phases_counter)
    assert len(phases_counter) > 0
    l_phases = phases_counter.data
    l_new_phases = [l_phases[0]]
    l_new_values = [l_values[0]]
    for idx in range(1, len(l_phases)):
        if l_phases[idx] > 2 and l_phases[idx - 1] > 2:
            l_new_values[-1]["GCSTW"].add_counter(l_values[idx]["GCSTW"])
            l_new_values[-1]["TOTALGC"].add_counter(l_values[idx]["GCSTW"])
            l_new_values[-1]["TOTAL"].add_counter(l_values[idx]["GCSTW"])
        else:
            if l_phases[idx] > 2:
                l_new_phases.append(2)
            else:
                l_new_phases.append(l_phases[idx])
            l_new_values.append(l_values[idx])
    new_phase_counter = copy.deepcopy(phases_counter)
    new_phase_counter.data = l_new_phases
    for idx in range(len(l_new_phases)):
        for phase_name in l_new_values[idx].keys():
            if phase_name not in jvm.BASE_PHASES:
                l_new_values[idx][phase_name] = parse_utils.get_empty_counter(
                    l_new_values[idx][phase_name]
                )
    assert len(l_new_values) == len(new_phase_counter)
    return new_phase_counter, l_new_values


def parse_statistics(l_counters: List, p_stats: str, end_stat_token: str) -> List:
    d_counters_idx_map = dict()
    for idx in range(len(l_counters)):
        l_events = l_counters[idx].get_events()
        for counter_event in l_events:
            if counter_event not in d_counters_idx_map:
                d_counters_idx_map[counter_event] = list()
            d_counters_idx_map[counter_event].append(idx)
    if len(l_counters) != len(d_counters_idx_map.keys()):
        l_counters_measured = list()
        for counter_event in d_counters_idx_map.keys():
            l_counters_measured += d_counters_idx_map[counter_event]
        assert len(set(l_counters_measured)) == len(l_counters)
    with utils.CommonFile(p_stats, "r") as f_stats:
        phase_idx = 0
        for line in f_stats:
            if end_stat_token in line:
                phase_idx += 1
                continue
            line = line.strip()
            l_split = line.split()
            if len(l_split) >= 2:
                counter_name = l_split[0]
                if counter_name in d_counters_idx_map:
                    for counter_idx in d_counters_idx_map[counter_name]:
                        if l_split[1] == ".nan":
                            l_split[1] = 0.0
                        l_counters[counter_idx].add_value(
                            phase_idx, counter_name, l_split[1]
                        )
    return l_counters


def split_benchmark_path(p_benchmark: str) -> [str, str, int, str]:
    bm_name = p_benchmark.split("/")[-2]
    bm_gc = p_benchmark.split("/")[-1].split("_")[0]
    bm_heap = p_benchmark.split("/")[-1].split("_")[1]
    return bm_name, bm_gc, 0, bm_heap


def drop_disabled(l_counters: List, l_jdk_events: List) -> [List, List]:
    l_simulation_tmp_events = copy.deepcopy(l_jdk_events)
    while 0 in l_simulation_tmp_events:
        idx_to_drop = l_simulation_tmp_events.index(0)
        l_simulation_tmp_events.pop(idx_to_drop)
        for counter in l_counters:
            counter.drop_idx(idx_to_drop)
    return l_counters


def generate_gcstw_move(l_phases: List) -> List:
    l_move = [None] * len(l_phases)
    l_phases_post_move = list()
    num_valid_phases = 0
    for idx in range(len(l_phases)):
        if l_phases[idx] == 2:
            if idx == (len(l_phases) - 1):
                print(f"ERROR: GC pause with no application phase following it")
                assert False
            if l_phases[idx - 1] > 2:
                l_move[idx] = idx - 1
            elif l_phases[idx + 1] > 2:
                l_move[idx] = idx + 1
            elif l_phases[idx + 1] == 1 and l_phases[idx - 1] == 1:
                l_move[idx] = idx - 1
                print(f"WARN: GC pause with no work!")
            else:
                print(
                    f"ERRROR: Invalid index {l_phases[idx - 1]} -> {l_phases[idx]} -> {l_phases[idx + 1]}"
                )
                assert False
        else:
            num_valid_phases += 1
            l_phases_post_move.append(l_phases[idx])
    return l_move, num_valid_phases, l_phases_post_move


def get_list_of_counter_names(l_counters: List) -> [List, List]:
    l_concurrent = list()
    l_total = list()
    for counter in l_counters:
        if isinstance(counter["event"], dict) and "gc" in counter["event"]:
            l_concurrent.append(counter["name"])
        else:
            l_total.append(counter["name"])
    return l_concurrent, l_total


def convert_per_phase_list_to_dict(
    l_parse: List,
    empty_counter: "AbstractParseCounter",
    gc_id_to_event_map: Dict,
    phase_counter: "StaticCounter",
) -> Dict:
    d_total = jvm.get_phase_dict(empty_counter, gc_id_to_event_map)
    for k in d_total.keys():
        for idx in range(len(phase_counter)):
            d_total[k].add_counter(l_parse[idx][k])
        d_total[k] = d_total[k].finalize()
    new_phase_counter, l_new_parse = merge_gc_simulation_pauses(phase_counter, l_parse)
    d_per_phase = jvm.get_phase_dict(
        [None] * len(new_phase_counter), gc_id_to_event_map
    )
    for idx in range(len(new_phase_counter)):
        for k in d_total.keys():
            d_per_phase[k][idx] = l_new_parse[idx][k]
            d_per_phase[k][idx] = d_per_phase[k][idx].finalize()
    return d_total, d_per_phase, new_phase_counter


def generate_parsed_concurrent_counter(
    counter_name: str,
    l_data: List,
    phase_counter: "StaticCounter",
    gc_id_to_event_map: Dict,
) -> Dict:
    gc_counter = l_data[l_data.index(f"(gc){counter_name}")]
    nongc_counter = l_data[l_data.index(f"(nongc){counter_name}")]
    l_parse = list()
    if len(gc_counter) == 0:
        print("WARN: GC counter empty, assigning empty counter to None")
        empty_counter = parse_utils.get_empty_counter(parse_utils.ParseCounter(None))
    else:
        empty_counter = parse_utils.get_empty_counter(gc_counter.get_parse_counter(0))
    for idx in range(len(phase_counter)):
        d_phase = jvm.get_phase_dict(empty_counter, gc_id_to_event_map)
        jdk_phase_id = int(phase_counter.get_parse_counter(idx).to_string())
        jdk_phase = gc_id_to_event_map[jdk_phase_id]
        if jdk_phase_id > 2:
            d_phase[jdk_phase].add_counter(gc_counter.get_parse_counter(idx))
            d_phase["GCSTW"].add_counter(gc_counter.get_parse_counter(idx))
            # nongc_counter.get_parse_counter(idx).assert_zero() <- should be negligible but not necessarily zero
        elif jdk_phase_id == 1:
            d_phase["CONCURRENTGC"].add_counter(gc_counter.get_parse_counter(idx))
            d_phase["NONGC"].add_counter(nongc_counter.get_parse_counter(idx))
        d_phase["TOTALGC"].add_counter(d_phase["GCSTW"])
        d_phase["TOTALGC"].add_counter(d_phase["CONCURRENTGC"])
        d_phase["TOTAL"].add_counter(d_phase["TOTALGC"])
        d_phase["TOTAL"].add_counter(d_phase["NONGC"])
        l_parse.append(d_phase)
    return convert_per_phase_list_to_dict(
        l_parse, empty_counter, gc_id_to_event_map, phase_counter
    )


def generate_parsed_total_counter(
    counter_name: str,
    l_data: List,
    phase_counter: "StaticCounter",
    gc_id_to_event_map: Dict,
) -> Dict:
    total_counter = l_data[l_data.index(counter_name)]
    if len(total_counter) == 0:
        print("WARN: Total counter empty, assigning empty counter to None")
        empty_counter = parse_utils.get_empty_counter(parse_utils.ParseCounter(None))
    else:
        empty_counter = parse_utils.get_empty_counter(
            total_counter.get_parse_counter(0)
        )
    l_parse = list()
    for idx in range(len(phase_counter)):
        d_phase = jvm.get_phase_dict(empty_counter, gc_id_to_event_map)
        jdk_phase_id = int(phase_counter.get_parse_counter(idx).to_string())
        jdk_phase = gc_id_to_event_map[jdk_phase_id]
        if jdk_phase_id > 2:
            d_phase[jdk_phase].add_counter(total_counter.get_parse_counter(idx))
            d_phase["GCSTW"].add_counter(total_counter.get_parse_counter(idx))
        elif jdk_phase_id == 1:
            d_phase["NONGC"].add_counter(total_counter.get_parse_counter(idx))
        d_phase["TOTALGC"].add_counter(d_phase["GCSTW"])
        d_phase["TOTAL"].add_counter(d_phase["TOTALGC"])
        d_phase["TOTAL"].add_counter(d_phase["NONGC"])
        l_parse.append(d_phase)
    return convert_per_phase_list_to_dict(
        l_parse, empty_counter, gc_id_to_event_map, phase_counter
    )


def generate_parsed_counters(
    d_data: Dict, y_counter_def: "yaml.YAMLObject", gc_id_to_event_map: Dict, key: str
) -> Dict:
    l_concurrent, l_total = get_list_of_counter_names(y_counter_def[key])
    l_data = d_data[key]
    jdk_counter = l_data[l_data.index("jdkphase")]
    l_simulation_phases = jdk_counter.data
    d_total = dict()
    d_per_phase = dict()
    new_phase_counter = None
    for counter in l_concurrent:
        (
            d_counter_total,
            d_counter_per_phase,
            new_phase_counter,
        ) = generate_parsed_concurrent_counter(
            counter, l_data, jdk_counter, gc_id_to_event_map
        )
        d_total[counter] = d_counter_total
        d_per_phase[counter] = d_counter_per_phase
    for counter in l_total:
        (
            d_counter_total,
            d_counter_per_phase,
            new_phase_counter,
        ) = generate_parsed_total_counter(
            counter, l_data, jdk_counter, gc_id_to_event_map
        )
        d_total[counter] = d_counter_total
        d_per_phase[counter] = d_counter_per_phase
    l_new_simulation_phases = list()
    if new_phase_counter is not None:
        l_new_simulation_phases = new_phase_counter.data
    return d_total, d_per_phase, l_new_simulation_phases


def get_gc_cpu_percent(l_data: List) -> List:
    s_num_gc_counters = 0
    s_num_nongc_counters = 0
    for counter in l_data:
        if counter.name == f"(gc)insts":
            s_num_gc_counters += 1
        elif counter.name == f"(nongc)insts":
            s_num_nongc_counters += 1
    assert s_num_gc_counters == s_num_nongc_counters
    l_gc_counters = [0] * s_num_gc_counters
    l_nongc_counters = [0] * s_num_nongc_counters
    l_division_counters = [None] * s_num_gc_counters
    for counter in l_data:
        if counter.name == f"(gc)insts":
            counter_idx = int(counter.multiplier)
            l_gc_counters[counter_idx] = sum(counter.data)
        elif counter.name == f"(nongc)insts":
            counter_idx = int(counter.multiplier)
            l_nongc_counters[counter_idx] = sum(counter.data)
    total_counters = float(0.0)
    for counter_idx in range(len(l_gc_counters)):
        if l_gc_counters[counter_idx] > 0 and l_nongc_counters[counter_idx] > 0:
            total_counters = l_gc_counters[counter_idx] + l_nongc_counters[counter_idx]
            l_division_counters[counter_idx] = float(
                l_gc_counters[counter_idx]
            ) / float(total_counters)
        elif l_gc_counters[counter_idx] > 0 and l_nongc_counters[counter_idx] == 0:
            l_division_counters[counter_idx] = 1.0
        elif l_gc_counters[counter_idx] == 0 and l_nongc_counters[counter_idx] > 0:
            l_division_counters[counter_idx] = 0.0
    return l_division_counters


def generate_expected_execution_logs(p_outdir: str) -> List:
    config = utils.parse_yaml(f"{p_outdir}/config.yaml")
    l_expected_executions = list()
    for bm_name in config["benchmark"]:
        p_benchmark = f"{p_outdir}/{bm_name}"
        if os.path.exists(p_benchmark):
            p_execution_list = list()
            for execution_folder in os.scandir(p_benchmark):
                if execution_folder.is_dir():
                    if execution_folder.name not in [
                        "scripts",
                        "checkpoint",
                        "jdk",
                    ]:
                        p_execution_list.append(execution_folder.path)
            l_expected_executions += p_execution_list
        if len(p_execution_list) == 0:
            l_expected_executions.append(p_benchmark)
    return l_expected_executions


def combine_check_dict(
    l_executions: List, framework: str, _split_benchmark_path: Callable
) -> Dict:
    d_benchmark = check.generate_execution_dict(
        l_executions, NUM_MAX_ATTEMPTS, _split_benchmark_path
    )
    for p_benchmark in l_executions:
        d_execution_check = utils.parse_yaml(f"{p_benchmark}/{framework}/check.yaml")
        assert len(list(d_execution_check.keys())) == 1
        b_hash = list(d_execution_check.keys())[0]
        assert b_hash in d_benchmark
        d_benchmark[b_hash] = copy.deepcopy(d_execution_check[b_hash])
    return d_benchmark


def combine_parse(p_outdir: str, l_process: str, framework: str) -> None:
    d_perf = dict()
    for p_process in l_process:
        d_perf[p_process] = utils.parse_json(
            f"{p_process}/{framework}/results_map.json"
        )
    utils.save_json(d_perf, f"{p_outdir}/results_map.json")
    l_combined_results = combine.combine_into_per_benchmark(
        d_perf,
        jvm.EXPECTED_SIMULATION_ITERATIONS,
        split_benchmark_path,
    )
    utils.save_json(l_combined_results, f"{p_outdir}/results.json")


def get_counters(p_counters: str) -> list:
    y_perf = utils.parse_yaml(p_counters)
    l_counters = list()
    for k in y_perf:
        for counter in y_perf[k]:
            l_counters.append(counter["name"])
    return l_counters + AGENT_COUNTERS, l_counters
