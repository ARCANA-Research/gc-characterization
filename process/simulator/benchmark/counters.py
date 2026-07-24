# {@code counters.py} analysis simulation statistics data to generate
# {@code parse.yaml} file that contains the values for all counters of
# interest. This simplifies parsing code.

import argparse
import copy
import os
import sys

from typing import Dict, List, Set

sys.path.append(os.path.abspath("support"))
from common import jvm, op, progress, utils
from common.simulation import (
    counter_utils,
    gem5,
    ramulator2,
    sample_utils,
    simulation_utils,
)


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--outdir", required=True, nargs=1)
    parser.add_argument("--execution", required=True, nargs=1)
    parser.add_argument("--sampled", required=False, action="store_true")
    args = parser.parse_args()
    p_curr = utils.get_currdir()
    p_outdir = args.outdir[0]
    p_execution = args.execution[0]
    p_counter = f"{p_curr}/support/simulator/stats/counters.yaml"
    config = utils.parse_yaml(f"{p_outdir}/config.yaml")
    progress_bar = progress.start(f"Generating Counters -> {p_execution}", 1)
    bm_name, bm_gc, _, bm_heap = simulation_utils.split_benchmark_path(p_execution)
    p_simerr = f"{p_execution}/simerr.log"
    p_gem5_stats = f"{p_execution}/stats.gz"
    p_ramulator2_stats = f"{p_execution}/ramulator_stats.gz"
    if args.sampled == True:
        p_simerr = sample_utils.get_sample_path(p_simerr)
        p_gem5_stats = sample_utils.get_sample_path(p_gem5_stats)
        p_ramulator2_stats = sample_utils.get_sample_path(p_ramulator2_stats)
    l_jdk_events = gem5.parse_simerr(p_simerr)
    num_phases = len(l_jdk_events)
    y_counter = utils.parse_yaml(p_counter)
    l_gem5_counters = gem5.generate_counters(
        y_counter, config, p_gem5_stats, num_phases, l_jdk_events
    )
    l_ramulator2_counters = ramulator2.generate_counters(
        y_counter, p_ramulator2_stats, num_phases, l_jdk_events
    )
    p_benchmark_base = "/".join(p_execution.split("/")[:-2])
    bm_minheap = jvm.get_benchmark_heap(
        bm_name, 1.0, f"{p_benchmark_base}/running/configs/{bm_gc}.yaml"
    )
    bm_heap = int(bm_heap)
    heap_multiplier = bm_heap / bm_minheap
    gc_thread_count = utils.count_string_instances(p_simerr, ["GC THREAD START"])[0]
    if gc_thread_count == 0:
        gc_thread_count = utils.count_string_instances(
            p_simerr, ["ADDING GC THREAD TID"]
        )[0]
    if "running_size" in config:
        running_size = config["running_size"]
    else:
        running_size = config["size"]
    d_benchmark = {
        "benchmark": bm_name,
        "gc": bm_gc,
        "iteration": 0,
        "heap": bm_heap,
        "heap_multiplier": heap_multiplier,
        "running_size": running_size,
        "path": p_execution,
        "data": {
            "gc_thread_count": gc_thread_count,
        },
        "sampled": args.sampled,
    }
    d_benchmark_no_combine = copy.deepcopy(d_benchmark)
    d_benchmark_no_combine["data"]["gem5"] = counter_utils.counters_list_to_yaml(
        l_gem5_counters, False
    )
    d_benchmark_no_combine["data"]["ramulator2"] = counter_utils.counters_list_to_yaml(
        l_ramulator2_counters, False
    )
    p_benchmark_output = f"{p_execution}/simulator"
    utils.create_folder_if_not_exist(p_benchmark_output)
    utils.save_yaml(
        d_benchmark_no_combine, f"{p_benchmark_output}/parse_nocombine.yaml"
    )

    d_benchmark_combine = copy.deepcopy(d_benchmark)
    d_benchmark_combine["data"]["gem5"] = counter_utils.counters_list_to_yaml(
        l_gem5_counters, True
    )
    d_benchmark_combine["data"]["ramulator2"] = counter_utils.counters_list_to_yaml(
        l_ramulator2_counters, True
    )
    utils.save_yaml(d_benchmark_combine, f"{p_benchmark_output}/parse.yaml")
    progress.advance(progress_bar)
    progress.end(progress_bar)


if __name__ == "__main__":
    main()
