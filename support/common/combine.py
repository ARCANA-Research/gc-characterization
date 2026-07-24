import copy
import os
import subprocess

from typing import Callable, Dict, List

from common import check, utils, progress


def get_executions(p_outdir: str) -> List:
    l_executions = list()
    for f_execution in os.scandir(p_outdir):
        if "results" in f_execution.path:
            continue
        if "excel" in f_execution.path:
            continue
        if f_execution.is_dir():
            l_executions.append(f_execution.path)
    l_executions.sort()
    return l_executions


def update_check_execution_table(d_execution: Dict, p_check_table: Dict) -> Dict:
    d_check_table = utils.parse_yaml(p_check_table)
    for b_hash in d_check_table.keys():
        if b_hash not in d_execution:
            d_execution[b_hash] = d_check_table[b_hash]
        else:
            if d_check_table[b_hash]["PROCESS"] == check.Status.PASSED:
                d_execution[b_hash] = d_check_table[b_hash]
    return d_execution


def combine_into_per_benchmark(
    d_perf: Dict, iterations: int, split_benchmark_path: Callable
) -> List:
    d_combined = dict()
    for p_benchmark in d_perf:
        b_hash = check.get_benchmark_hash(p_benchmark, split_benchmark_path)
        d_data = d_perf[p_benchmark]
        if b_hash not in d_combined:
            d_combined[b_hash] = {
                "benchmark": d_data["benchmark"],
                "gc": d_data["gc"],
                "heap": d_data["heap"],
                "heap_multiplier": d_data["heap_multiplier"],
                "data": list(),
            }
        d_combined[b_hash]["data"].append(d_data)
    for b_hash in d_combined:
        assert len(d_combined[b_hash]["data"]) == iterations
    return list(d_combined.values())


def check_if_same_config(l_executions: List) -> bool:
    progress_bar = progress.start("Checking Configs", len(l_executions))
    y_expected_config = None
    for p_execution in l_executions:
        y_config = utils.parse_yaml(f"{p_execution}/config.yaml")
        del y_config["benchmark"]
        if "gc" in y_config:
            del y_config["gc"]
        if "simulation" in y_config:
            del y_config["simulation"]["output"]
        if "checkpoint" in y_config:
            del y_config["checkpoint"]["setup"]
        if "gem5" in y_config:
            if "binary" in y_config["gem5"]:
                del y_config["gem5"]["binary"]
            if "mount-image" in y_config["gem5"]:
                del y_config["gem5"]["mount-image"]
            if "simulation-build" in y_config["gem5"]:
                del y_config["gem5"]["simulation-build"]
            if "simulation" in y_config["gem5"]:
                del y_config["gem5"]["simulation"]
            if "jfr" in y_config["gem5"]:
                del y_config["gem5"]["jfr"]
        if "debug" in y_config:
            del y_config["debug"]
        if "running-ng" in y_config:
            if "config" in y_config["running-ng"]:
                del y_config["running-ng"]["config"]
        if "counter" in y_config:
            if "max-attempts" in y_config["counter"]:
                del y_config["counter"]["max-attempts"]
        if y_expected_config is None:
            y_expected_config = copy.deepcopy(y_config)
        if utils.compare_dict(y_expected_config, y_config) == False:
            print(f"Invalid config -> {p_execution}")
            return False
        progress.advance(progress_bar)
    progress.end(progress_bar)
    return True
