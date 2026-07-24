import argparse
import os
import sys

from typing import Callable, Dict, List

sys.path.append(os.path.abspath("support"))
from common import check, check_table, jvm, progress, utils
from common.simulation import (
    check_utils,
    counter_utils,
    gem5,
    ramulator2,
    sample_utils,
    simulation_utils,
)


def check_if_log_valid(p_log: str) -> bool:
    with utils.CommonFile(p_log, "r") as f_log:
        try:
            num_lines = 0
            for line in f_log:
                num_lines += 1
        except Exception as e:
            return False
    return True


def check_dacapo_execution(d_event_state: Dict, p_execution: str) -> Dict:
    p_dacapo = f"{p_execution}/board.pc.com_1.device"
    b_output_found = os.path.isfile(p_dacapo)
    d_event_state["OUTPUT_FOUND"] = check.Status.from_bool(b_output_found)
    if b_output_found == False:
        return d_event_state
    query_bool = utils.check_file_has_strings(
        p_dacapo,
        [
            "PASSED in",
            "Validation FAILED",
            "starting =",
            ".OutOfMemoryError",
            "compute_tree_cost",
        ],
    )
    d_event_state["DACAPO_STARTED"] = check.Status.from_bool(query_bool[2])
    d_event_state["NO_DACAPO_FAILED"] = check.Status.from_bool(not query_bool[1])
    d_event_state["DACAPO_PASSED"] = check.Status.from_bool(query_bool[0])
    d_event_state["NO_JAVA_OOM"] = check.Status.from_bool(not query_bool[3])
    d_event_state["NO_C2_FAILED"] = check.Status.from_bool(not query_bool[4])
    return d_event_state


def check_execution_sample(
    d_event_state: Dict,
    p_execution: str,
    p_eventmap: str,
    create_ramulator2_trace: bool,
    split_benchmark_path: Callable,
) -> Dict:
    if d_event_state["DACAPO_PASSED"] == check.Status.PASSED:
        d_event_state["SAMPLE"] = check.Status.DISREGARD
        return d_event_state
    for k_status in d_event_state:
        if (
            k_status != "DACAPO_PASSED"
            and k_status not in check.BASE_EVENTS
            and k_status.ctype == check.ColumnType.BOOLEAN
            and k_status != "CONDOR_TERMINATED"
            and k_status not in sample_utils.STAT_COUNTERS
        ):
            if d_event_state[k_status] != check.Status.PASSED:
                d_event_state["SAMPLE"] = check.Status.FAILED
                return d_event_state
    b_sample_success = sample_utils.generate_sample_statistics(p_execution)
    if b_sample_success == False:
        d_event_state["SAMPLE"] = check.Status.FAILED
        return d_event_state
    d_event_state = gem5.check_gem5_statistics(
        d_event_state, p_execution, p_eventmap, split_benchmark_path, True
    )
    d_event_state = ramulator2.check_ramulator2_execution(
        d_event_state, p_execution, p_eventmap, create_ramulator2_trace, True
    )
    for k_status in sample_utils.STAT_COUNTERS:
        if d_event_state[k_status] == check.Status.FAILED:
            d_event_state["SAMPLE"] = check.Status.FAILED
            return d_event_state
    d_event_state["SAMPLE"] = check.Status.PASSED
    return d_event_state


def generate_events(
    p_execution: List,
    p_outdir: str,
    p_status: str,
    create_ramulator2_trace: bool,
    split_benchmark_path: Callable,
    p_support: str,
) -> Dict:
    config = utils.parse_yaml(f"{p_outdir}/config.yaml")
    d_benchmark = check.generate_execution_dict(
        [p_execution], simulation_utils.NUM_MAX_ATTEMPTS, split_benchmark_path
    )
    p_eventmap = f"{p_outdir}/eventmap.yaml"
    d_event_state = check.generate_event_status_dict(p_status, False)
    d_event_state = check_utils.check_condor_execution(d_event_state, p_execution)
    d_event_state = gem5.check_gem5_execution(
        d_event_state, p_execution, p_eventmap, split_benchmark_path
    )
    d_event_state = gem5.check_gem5_simout(d_event_state, p_execution)
    d_event_state = ramulator2.check_ramulator2_execution(
        d_event_state, p_execution, p_eventmap, create_ramulator2_trace
    )
    d_event_state = check_dacapo_execution(d_event_state, p_execution)
    d_event_state = check.check_correct_heap(
        d_event_state, config, p_support, p_execution, split_benchmark_path
    )
    d_event_state = check_execution_sample(
        d_event_state,
        p_execution,
        p_eventmap,
        create_ramulator2_trace,
        split_benchmark_path,
    )
    b_hash = check.get_benchmark_hash(p_execution, split_benchmark_path)
    _, _, bm_iteration, _ = split_benchmark_path(p_execution)
    d_benchmark[b_hash]["EXECUTION"][bm_iteration] = d_event_state
    d_benchmark[b_hash]["PATHS"][bm_iteration] = p_execution
    return d_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--execution", required=True)
    args = parser.parse_args()
    p_outdir = args.outdir
    p_execution = args.execution
    progress_bar = progress.start(f"Checking -> {p_execution}", 1)
    p_curr = utils.get_currdir()
    p_support = f"{p_curr}/support"
    p_status = f"{p_support}/simulator/statusmap.yaml"
    config = utils.parse_yaml(f"{p_outdir}/config.yaml")
    d_benchmark = generate_events(
        p_execution,
        p_outdir,
        p_status,
        config["hardware"]["ramulator2"]["create_trace"],
        simulation_utils.split_benchmark_path,
        f"{p_curr}/support",
    )
    p_execution_output = f"{p_execution}/simulator"
    utils.create_folder_if_not_exist(p_execution_output)
    utils.save_yaml(d_benchmark, f"{p_execution_output}/check.yaml")
    progress.advance(progress_bar)
    progress.end(progress_bar)


if __name__ == "__main__":
    main()
