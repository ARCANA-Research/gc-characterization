import argparse
import os
import sys

sys.path.append(os.path.abspath("support"))
from common import jvm, progress, utils
from common.simulation import simulation_utils


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--outdir", required=True, nargs=1)
    parser.add_argument("--execution", required=True, nargs=1)
    args = parser.parse_args()
    p_outdir = args.outdir[0]
    p_execution = args.execution[0]
    progress_bar = progress.start(f"Parsing -> {p_execution} ->", 1)
    p_curr = utils.get_currdir()
    p_counter = f"{p_curr}/support/simulator/stats/counters.yaml"
    y_counter_def = utils.parse_yaml(p_counter)
    p_eventmap = f"{p_curr}/support/eventmap.yaml"
    d_perf = list()
    p_execution_output = f"{p_execution}/simulator"
    d_benchmark = utils.parse_yaml(f"{p_execution_output}/parse.yaml")
    _, gc_id_to_event_map, _ = jvm.valid_phases(
        p_eventmap, d_benchmark["gc"], True, False
    )
    (
        d_gem5_total,
        d_gem5_per_phase,
        l_gem5_jdk_phases,
    ) = simulation_utils.generate_parsed_counters(
        d_benchmark["data"], y_counter_def, gc_id_to_event_map, "gem5"
    )
    (
        d_ramulator2_total,
        d_ramulator2_per_phase,
        l_ramulator2_jdk_phases,
    ) = simulation_utils.generate_parsed_counters(
        d_benchmark["data"], y_counter_def, gc_id_to_event_map, "ramulator2"
    )
    assert l_gem5_jdk_phases == l_ramulator2_jdk_phases
    d_total = d_gem5_total
    d_total.update(d_ramulator2_total)
    d_per_phase = d_gem5_per_phase
    d_per_phase.update(d_ramulator2_per_phase)
    d_perf = {
        "benchmark": d_benchmark["benchmark"],
        "gc": d_benchmark["gc"],
        "heap": d_benchmark["heap"],
        "heap_multiplier": d_benchmark["heap_multiplier"],
        "running_size": d_benchmark["running_size"],
        "iteration": d_benchmark["iteration"],
        "data": d_total,
        "per_phase": {
            "data": d_per_phase,
            "phases": l_gem5_jdk_phases,
        },
        "sampled": d_benchmark["sampled"],
    }
    d_parse_nosplit = utils.parse_yaml(f"{p_execution_output}/parse_nocombine.yaml")
    d_perf["data"]["GC_CPU_PERCENT"] = {
        "TOTAL": simulation_utils.get_gc_cpu_percent(d_parse_nosplit["data"]["gem5"])
    }
    d_perf["data"]["GC_PHASE_COUNT"] = {"TOTAL": len(l_gem5_jdk_phases)}
    d_perf["data"]["GC_THREAD_COUNT"] = {
        "TOTAL": d_parse_nosplit["data"]["gc_thread_count"]
    }
    utils.save_json(d_perf, f"{p_execution_output}/results_map.json")
    progress.advance(progress_bar)
    progress.end(progress_bar)


if __name__ == "__main__":
    main()
