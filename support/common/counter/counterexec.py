import copy
import os
import shutil

from enum import Enum
from typing import Dict, List

from common import check, check_table, combine, jvm, progress, utils


class ExecutionParams(Enum):
    DEBUG = "DEBUG ENABLED"
    COUNTER_EVENTS = "COUNTER GC EVENTS"
    PER_THREAD_MEASUREMENT = "PER THREAD MEASUREMENT"
    PER_THREAD_DATA = "PER THREAD DATA"
    CONCURRENT_GC = "CONCURRENT GC"
    PERF_COUNTERS = "PERFORMANCE COUNTERS"
    PER_PHASE_COUNTERS = "PER PHASE COUNTERS"
    TYPE = "COUNTER:"


def parse_boolean_character(ch: str) -> bool:
    if ch == "❌":
        return False
    if ch == "✅":
        return True
    print(ch)
    assert False


def parse_execution_params(p_run: str) -> Dict:
    if os.path.isfile(p_run) is False:
        print(f"PARSEERROR: {p_run} not a file")
        return None
    d_execution_params = dict()
    f_run = open(p_run, "r")
    for line in f_run:
        if "COUNTER:" in line:
            if len(line.split()) == 2:
                d_execution_params[ExecutionParams.TYPE] = line.split()[-1]
        else:
            for param in ExecutionParams:
                if param.value in line:
                    d_execution_params[param] = parse_boolean_character(line.split()[0])
    expected_keys = set([param for param in ExecutionParams])
    if len(d_execution_params.keys()) != expected_keys:
        for key in expected_keys:
            if key not in d_execution_params:
                d_execution_params[key] = False
    assert set(d_execution_params.keys()) == expected_keys
    return d_execution_params


def split_benchmark_path(p_benchmark: str) -> [str, str, int, str]:
    bm_name = p_benchmark.split("/")[-2]
    bm_gc = p_benchmark.split("/")[-1].split("_")[0]
    bm_iteration = int(p_benchmark.split("/")[-1].split("_")[1])
    bm_heap = int(p_benchmark.split("/")[-1].split("_")[2])
    return bm_name, bm_gc, bm_iteration, bm_heap


def check_if_same_counters(l_executions: List, p_outdir: str, p_artifact: str) -> None:
    s_expected_counters = None
    s_drop_counters = set()
    for p_execution in l_executions:
        s_counters = set(
            utils.parse_yaml(f"{p_execution}/counters.yaml")["PERF"]["counters"]
        )
        if s_expected_counters is None:
            s_expected_counters = s_counters
        assert s_counters == s_expected_counters
    l_all_drop_concurrent = utils.parse_yaml(
        f"{p_artifact}/counters/drop-concurrent.yaml"
    )
    l_counters = list(s_expected_counters)
    l_drop_concurrent = list()
    for counter in l_counters:
        if counter in l_all_drop_concurrent:
            l_drop_concurrent.append(counter)
    d_counters = {
        "PERF": {"counters": l_counters, "drop_concurrent": l_drop_concurrent}
    }
    utils.save_yaml(d_counters, f"{p_outdir}/counters.yaml")


def check_if_same_config(l_executions: List, p_outdir: str) -> None:
    assert len(l_executions) > 0
    assert combine.check_if_same_config(l_executions) == True
    config = utils.parse_yaml(f"{l_executions[0]}/config.yaml")
    if "use_lbo_heap" in config["jdk"]:
        b_lbo_heap = config["jdk"]["use_lbo_heap"]
    else:
        b_lbo_heap = config["jdk"]["use-lbo-heap"]
    if "running_size" in config:
        running_size = config["running_size"]
    elif "size" in config:
        running_size = config["size"]
    else:
        running_size = "default"
    if "suite" in config:
        bm_suite = config["suite"]
    else:
        bm_suite = "dacapo"
    d_config = {
        "jdk": {
            "use-lbo-heap": b_lbo_heap,
            "heap-multiplier": config["jdk"]["heap-multiplier"],
        },
        "size": running_size,
        "suite": bm_suite,
        "gc": jvm.GC_LIST,
        "counter": {
            "iterations": config["counter"]["iterations"],
            "jvm-cpus": config["counter"]["jvm-cpus"],
            "gc-cpus": config["counter"]["gc-cpus"],
        },
    }
    utils.save_yaml(d_config, f"{p_outdir}/config.yaml")


def combine_check(l_executions: List, p_outdir: str, p_artifact: str) -> None:
    p_support = f"{p_artifact}/support"
    d_execution = dict()
    for p_execution in l_executions:
        d_execution = combine.update_check_execution_table(
            d_execution, f"{p_execution}/check_table.yaml"
        )
    check.generate_check_file(
        p_outdir, d_execution, split_benchmark_path, jvm.GC_LIST, True, False
    )
    table = check_table.generate_table(
        d_execution,
        f"{p_support}/counter/statusmap.yaml",
        split_benchmark_path,
        True,
        jvm.EXPECTED_COUNTER_ITERATIONS,
    )
    utils.write_to_file(table, f"{p_outdir}/check.ansi")
    utils.save_yaml(d_execution, f"{p_outdir}/check_table.yaml")


def check_if_same_eventmap(l_executions: List, p_outdir: str) -> None:
    y_expected_eventmap = None
    for p_execution in l_executions:
        y_eventmap = utils.parse_yaml(f"{p_execution}/eventmap.yaml")
        if y_expected_eventmap is None:
            y_expected_eventmap = copy.deepcopy(y_eventmap)
        if y_expected_eventmap != y_eventmap:
            print(f"COUNTERERROR: Invalid config -> {p_execution}")
            sys.exit(1)
    utils.save_yaml(y_expected_eventmap, f"{p_outdir}/eventmap.yaml")


def generate_gc_running_config(p_outdir: str, p_support: str) -> None:
    p_configs = f"{p_outdir}/running/configs"
    os.makedirs(f"{p_outdir}/running", exist_ok=True)
    if os.path.exists(p_configs) == True:
        shutil.rmtree(p_configs)
    os.makedirs(p_configs)
    for gc in jvm.GC_LIST:
        config = utils.parse_yaml(f"{p_outdir}/config.yaml")
        d_minheap = jvm.get_gc_minheap(p_support, gc, config)
        d_gc_config = {
            "suites": {
                "combined": {
                    "minheap": "counter-config",
                    "minheap_values": {"counter-config": d_minheap},
                }
            }
        }
        utils.save_yaml(d_gc_config, f"{p_configs}/{gc}.yaml")


def combine_analysis(l_group: List, p_outdir: str) -> None:
    s_title = set()
    l_analysis = list()
    progress_bar = progress.start(f"Combining Analysis -> {p_outdir}", len(l_group))
    for p_group_dir in l_group:
        l_group_analysis = utils.parse_json(f"{p_group_dir}/analysis.json")
        for d_analysis in l_group_analysis:
            if d_analysis["title"] not in s_title:
                l_analysis.append(d_analysis)
                s_title.add(d_analysis["title"])
        progress.advance(progress_bar)
    progress.end(progress_bar)
    utils.save_json(l_analysis, f"{p_outdir}/analysis.json")
