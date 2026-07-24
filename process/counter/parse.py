import argparse
import os
import sys

from collections import defaultdict
from enum import Enum
from typing import Dict, List, Set

sys.path.append(os.path.abspath("support"))
from common import combine, jfr, jvm, op, progress, utils
from common.counter import counterexec


def get_jfr_path(p_perf: str) -> str:
    return p_perf.replace("_perf.log", ".jfr")


def can_parse_jfr(p_perf: str) -> bool:
    return os.path.exists(get_jfr_path(p_perf))


def parse_gc_cpu_percent(p_perf: str, config: "yaml.YAMLObject") -> Dict:
    p_verify = p_perf.replace("_perf.log", "_verify.yaml")
    y_verify = utils.parse_yaml(p_verify)
    l_cpus = list(set(config["counter"]["jvm-cpus"] + config["counter"]["gc-cpus"]))
    l_cpus.sort()
    cpu_count = len(l_cpus)
    if y_verify["threads"] is None:
        return [None] * cpu_count
    l_nongc_cpu_execution = [0] * cpu_count
    l_nongc_num_threads = [0] * cpu_count
    l_gc_cpu_execution = [0] * cpu_count
    l_gc_num_threads = [0] * cpu_count
    for thread_exec in y_verify["threads"]:
        exec_time = int(thread_exec["time"].replace("%", ""))
        if thread_exec["execution_cpu"] is None:
            continue
        for cpu_exec in thread_exec["execution_cpu"]:
            if thread_exec["type"] == "JVM":
                cpu_idx = l_cpus.index(cpu_exec)
                l_nongc_cpu_execution[cpu_idx] += exec_time
                l_nongc_num_threads[cpu_idx] += 1
            elif thread_exec["type"] == "GC":
                cpu_idx = l_cpus.index(cpu_exec)
                l_gc_cpu_execution[cpu_idx] += exec_time
                l_gc_num_threads[cpu_idx] += 1
    l_gc_cpu_percentage = [None] * cpu_count
    l_num_threads = [0] * cpu_count
    for idx in range(len(l_gc_cpu_percentage)):
        if l_nongc_num_threads[idx] == 0 and l_gc_num_threads[idx] == 0:
            continue
        l_gc_cpu_percentage[idx] = op.op_divide(
            l_gc_cpu_execution[idx],
            op.op_add(l_nongc_cpu_execution[idx], l_gc_cpu_execution[idx]),
        )
        l_num_threads[idx] = op.op_add(l_nongc_num_threads[idx], l_gc_num_threads[idx])
    return l_gc_cpu_percentage


def parse_agent_data(
    agent_data: List, gc_event_to_id_map: Dict, d_execution_params: Dict
) -> Dict:
    d_data = jvm.get_base_phase_dict(0)
    if d_execution_params[counterexec.ExecutionParams.COUNTER_EVENTS] == False:
        d_data["GCSTW"] = agent_data[gc_event_to_id_map["GC_STW"]]
    else:
        for event in gc_event_to_id_map:
            assert gc_event_to_id_map[event] != 2
            if gc_event_to_id_map[event] > 2:
                d_data["GCSTW"] += agent_data[gc_event_to_id_map[event]]
                d_data[event] = agent_data[gc_event_to_id_map[event]]
    d_data["NONGC"] = agent_data[gc_event_to_id_map["JVM"]]
    d_data["TOTALGC"] = d_data["GCSTW"]
    d_data["TOTAL"] = d_data["TOTALGC"] + d_data["NONGC"]
    return d_data


def merge_gc_pauses(l_phases: List, l_values: List) -> [List, List]:
    assert len(l_phases) == len(l_values)
    assert len(l_phases) > 0
    l_new_phases = [l_phases[0]]
    l_new_values = [l_values[0]]
    for idx in range(1, len(l_phases)):
        if l_phases[idx] > 2 and l_phases[idx - 1] > 2:
            l_new_values[-1] = op.op_add(l_new_values[-1], l_values[idx])
        else:
            if l_phases[idx] > 2:
                l_new_phases.append(2)
            else:
                l_new_phases.append(l_phases[idx])
            l_new_values.append(l_values[idx])
    return l_new_phases, l_new_values


def parse_agent_data_per_phase(
    agent_data: List,
    gc_event_to_id_map: Dict,
    gc_id_to_event_map: Dict,
    d_execution_params: Dict,
) -> Dict:
    l_phases = agent_data["phases"]
    l_values = agent_data["values"]
    l_phases, l_values = merge_gc_pauses(l_phases, l_values)
    assert len(l_phases) == len(l_values)
    d_data = jvm.get_base_phase_dict([0] * len(l_phases))
    d_event_count = jvm.get_base_phase_dict(0)
    for event in gc_event_to_id_map:
        if gc_event_to_id_map[event] != 1:
            d_data[event] = [0] * len(l_phases)
            d_event_count[event] = 0
    for idx in range(len(l_values)):
        val = l_values[idx]
        phase = l_phases[idx]
        if phase == gc_event_to_id_map["JVM"]:
            d_data["NONGC"][idx] = val
            d_event_count["NONGC"] += 1
        elif phase < 2:
            assert False
        else:
            if phase > 2:
                d_data[gc_id_to_event_map[phase]][idx] = val
                d_event_count[gc_id_to_event_map[phase]] += 1
            d_data["GCSTW"][idx] = val
            d_data["TOTALGC"][idx] = val
            d_event_count["GCSTW"] += 1
            d_event_count["TOTALGC"] += 1
    d_data["TOTAL"] = op.op_binary(d_data["TOTALGC"], d_data["NONGC"], op.op_add)
    d_event_count["TOTAL"] = op.op_binary(
        d_event_count["TOTALGC"], d_event_count["NONGC"], op.op_add
    )
    return d_data, l_phases, d_event_count


def combine_perf_data(
    gc_data: List, jvm_data: List, gc_event_to_id_map: Dict, d_execution_params: Dict
) -> Dict:
    d_data = jvm.get_base_phase_dict(0)
    if gc_data is not None:
        d_data["CONCURRENTGC"] = gc_data[gc_event_to_id_map["JVM"]]
    if d_execution_params[counterexec.ExecutionParams.COUNTER_EVENTS] == False:
        d_data["GCSTW"] = jvm_data[gc_event_to_id_map["GC_STW"]]
    else:
        for event in gc_event_to_id_map:
            assert gc_event_to_id_map[event] != 2
            if gc_event_to_id_map[event] > 2:
                d_data["GCSTW"] += jvm_data[gc_event_to_id_map[event]]
                d_data[event] = jvm_data[gc_event_to_id_map[event]]
    d_data["NONGC"] = jvm_data[gc_event_to_id_map["JVM"]] - d_data["CONCURRENTGC"]
    d_data["TOTALGC"] = d_data["GCSTW"] + d_data["CONCURRENTGC"]
    d_data["TOTAL"] = d_data["TOTALGC"] + d_data["NONGC"]
    return d_data


def get_gc_thread_overlap(l_gc_threads: List, l_jvm_threads: List) -> float:
    s_gc_cpus = set(l_gc_threads)
    s_jvm_cpus = set(l_jvm_threads)
    return float(len(s_jvm_cpus.intersection(s_gc_cpus))) / float(len(s_jvm_cpus))


def parse_benchmark_stats(
    p_perf: str,
    p_outdir: str,
    p_eventmap: str,
    config: "yaml.YAMLObject",
    s_drop_concurrent_counters: Set,
    d_jfr_event: Dict,
):
    bm_name, bm_gc, bm_iteration, bm_heap = counterexec.split_benchmark_path(p_perf)
    d_execution_params = counterexec.parse_execution_params(
        p_perf.replace("_perf", "_run")
    )
    b_counter_events = d_execution_params[counterexec.ExecutionParams.COUNTER_EVENTS]
    l_gc_events, gc_id_to_event_map, gc_event_to_id_map = jvm.valid_phases(
        p_eventmap, bm_gc, b_counter_events, not b_counter_events
    )
    bm_minheap = jvm.get_benchmark_heap(
        bm_name, 1.0, f"{p_outdir}/running/configs/{bm_gc}.yaml"
    )
    heap_multiplier = bm_heap / bm_minheap
    d_parsed = {
        "benchmark": bm_name,
        "gc": bm_gc,
        "iteration": bm_iteration,
        "heap": bm_heap,
        "data": dict(),
        "heap_multiplier": heap_multiplier,
    }
    if d_execution_params[counterexec.ExecutionParams.PER_PHASE_COUNTERS]:
        d_parsed["per_phase"] = {
            "data": dict(),
            "phases": None,
        }
    y_perf = utils.parse_yaml(p_perf)
    y_counters = utils.parse_yaml(f"{p_outdir}/counters.yaml")
    if d_execution_params[counterexec.ExecutionParams.PERF_COUNTERS] == True:
        for event in y_counters["PERF"]["counters"]:
            jvm_data = y_perf["JVM"][event]
            gc_data = None
            if (
                event not in s_drop_concurrent_counters
                and d_execution_params[counterexec.ExecutionParams.CONCURRENT_GC]
                == True
            ):
                gc_data = y_perf["GC"][event]
            d_parsed["data"][event] = combine_perf_data(
                gc_data, jvm_data, gc_event_to_id_map, d_execution_params
            )
    if d_execution_params[counterexec.ExecutionParams.PER_PHASE_COUNTERS]:
        d_parsed["data"]["TIME"] = parse_agent_data(
            y_perf["AGENT"]["TIME"]["total"], gc_event_to_id_map, d_execution_params
        )
        d_time_per_phase_data, l_phases, d_event_count = parse_agent_data_per_phase(
            y_perf["AGENT"]["TIME"],
            gc_event_to_id_map,
            gc_id_to_event_map,
            d_execution_params,
        )
        d_parsed["per_phase"]["data"]["TIME"] = d_time_per_phase_data
        d_parsed["per_phase"]["phases"] = l_phases
        d_parsed["data"]["GC_EVENT_COUNT"] = d_event_count
    else:
        d_parsed["data"]["TIME"] = parse_agent_data(
            y_perf["AGENT"]["TIME"], gc_event_to_id_map, d_execution_params
        )
        d_parsed["data"]["GC_EVENT_COUNT"] = parse_agent_data(
            y_perf["AGENT"]["GC_EVENT_COUNT"], gc_event_to_id_map, d_execution_params
        )
    if d_execution_params[counterexec.ExecutionParams.CONCURRENT_GC] == True:
        d_parsed["data"]["GC_THREAD_COUNT"] = {
            "TOTAL": y_perf["AGENT"]["GC_THREAD_COUNT"]
        }
    else:
        d_parsed["data"]["GC_THREAD_COUNT"] = {"TOTAL": 0}
    gc_thread_overlap = 0.0
    if d_execution_params[counterexec.ExecutionParams.PER_THREAD_MEASUREMENT] == True:
        gc_thread_overlap = get_gc_thread_overlap(
            y_perf["AGENT"]["GC_THREADS"], y_perf["AGENT"]["JVM_THREADS"]
        )
    d_parsed["data"]["GC_THREAD_OVERLAP"] = {"TOTAL": gc_thread_overlap}
    d_parsed["data"]["GC_CPU_PERCENT"] = {"TOTAL": parse_gc_cpu_percent(p_perf, config)}
    if can_parse_jfr(p_perf) == True:
        p_jfr = get_jfr_path(p_perf)
        p_jfr_json = jfr.get_jfr_json_path(config, p_jfr)
        l_events = jfr.get_jfr_event_objects(d_jfr_event, p_jfr_json)
        l_gc_reclaim, l_old_used_percent, l_objects_promoted = jfr.parse_gc_events(
            l_events
        )
        d_parsed["data"]["GC_RECLAIM_RATE"] = {"TOTALGC": l_gc_reclaim}
        d_parsed["data"]["GC_HEAP_USED_PERCENT_OLD"] = {"TOTALGC": l_old_used_percent}
        d_parsed["data"]["GC_OBJECT_PROMOTION"] = {"TOTALGC": l_objects_promoted}
    return d_parsed


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--outdir", required=True, nargs=1)
    args = parser.parse_args()
    p_outdir = args.outdir[0]
    p_eventmap = f"{p_outdir}/eventmap.yaml"
    p_config = f"{p_outdir}/config.yaml"
    config = utils.parse_yaml(f"{p_outdir}/config.yaml")
    num_iterations = config["counter"]["iterations"]
    y_check = utils.parse_yaml(f"{p_outdir}/check.yaml")
    d_perf = dict()
    p_artifact = utils.get_currdir()
    d_jfr_event = jfr.get_event_map()
    s_drop_concurrent_counters = set(
        utils.parse_yaml(f"{p_artifact}/counters/drop-concurrent.yaml")
    )
    progress_bar = progress.start(f"Parsing", len(y_check["PROCESS"]))
    for p_runlog in y_check["PROCESS"]:
        p_perf = p_runlog.replace("_run.log", "_perf.log")
        print(f"Processing -> {p_perf}")
        d_perf[p_runlog] = parse_benchmark_stats(
            p_perf,
            p_outdir,
            p_eventmap,
            config,
            s_drop_concurrent_counters,
            d_jfr_event,
        )
        progress.advance(progress_bar)
    progress.end(progress_bar)
    utils.save_json(d_perf, f"{p_outdir}/results_map.json")
    l_combined_results = combine.combine_into_per_benchmark(
        d_perf, num_iterations, counterexec.split_benchmark_path
    )
    utils.save_json(l_combined_results, f"{p_outdir}/results.json")


if __name__ == "__main__":
    main()
