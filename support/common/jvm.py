import copy
from enum import Enum
import yaml
from typing import Any, Dict, List

from common import utils

GC_LIST = ["G1", "Parallel", "Serial", "Shenandoah", "Z", "GenZ"]

NUM_GC_PHASES = 7
NUM_BASE_PHASES = 3
BASE_PHASES = ["TOTAL", "NONGC", "TOTALGC", "GCSTW", "CONCURRENTGC"]

BENCHMARK_LIST = {
    "dacapo": [
        "avrora",
        "batik",
        "biojava",
        "eclipse",
        "fop",
        "graphchi",
        "h2",
        "h2o",
        "jme",
        "jython",
        "luindex",
        "lusearch",
        "pmd",
        "spring",
        "sunflow",
        "tomcat",
        "xalan",
        "zxing",
    ],
    "renaissance": [
        "akka-uct",
        "als",
        "chi-square",
        "db-shootout",
        "dec-tree",
        "dotty",
        "finagle-chirper",
        "finagle-http",
        "fj-kmeans",
        "future-genetic",
        "gauss-mix",
        "log-regression",
        "mnemonics",
        "movie-lens",
        "naive-bayes",
        "page-rank",
        "par-mnemonics",
        "philosophers",
        "reactors",
        "scala-doku",
        "scala-kmeans",
    ],
}
BENCHMARK_SUITES = ["dacapo", "renaissance"]
BENCHMARK_SIZES = {"dacapo": ["small", "default", "large"], "renaissance": ["default"]}

# EXPECTED_COUNTER_ITERATIONS = 5  # todo account for different sizes of runs
EXPECTED_COUNTER_ITERATIONS = 3  # todo account for different sizes of runs
EXPECTED_SIMULATION_ITERATIONS = 1


def get_benchmark_heap(
    benchmark: str, heap_multiplier: float, p_running_config: str
) -> int:
    y_running = utils.parse_yaml(p_running_config)
    suite_name = list(y_running["suites"].keys())
    assert len(suite_name) == 1
    suite_name = suite_name[0]
    key_minheap = y_running["suites"][suite_name]["minheap"]
    dict_minheap_values = y_running["suites"][suite_name]["minheap_values"][key_minheap]
    return int(dict_minheap_values[benchmark] * heap_multiplier)


def valid_phases(
    p_eventmap: str, gc: str, custom_gc_events: bool, default_gc_events: bool
) -> [List, Dict, Dict]:
    y_map = utils.parse_yaml(p_eventmap)
    l_events = list()
    id_to_event_map = dict()
    event_to_id_map = dict()
    for b in y_map["Base"]:
        if default_gc_events is False and b == "GC_STW":
            continue
        l_events.append(y_map["Base"][b])
        id_to_event_map[int(y_map["Base"][b])] = b
    if custom_gc_events is True:
        for b in y_map[gc]:
            l_events.append(y_map[gc][b])
            id_to_event_map[int(y_map[gc][b])] = b
    for k in id_to_event_map.keys():
        event_to_id_map[id_to_event_map[k]] = k
    return l_events, id_to_event_map, event_to_id_map


def valid_custom_phases(p_eventmap: str) -> Dict:
    d_gc_phases = dict()
    for gc in GC_LIST:
        l_gc_events, gc_id_to_event_map, gc_event_to_id_map = valid_phases(
            p_eventmap, gc, True, False
        )
        # Remove base events
        for phase_id in range(NUM_BASE_PHASES):
            if phase_id in l_gc_events:
                l_gc_events.remove(phase_id)
        gc_start_phase = min(l_gc_events)
        d_gc_phases[gc] = dict()
        for phase_name in gc_event_to_id_map.keys():
            phase_id = gc_event_to_id_map[phase_name]
            if phase_id >= NUM_BASE_PHASES:
                assert phase_id - gc_start_phase >= 0
                d_gc_phases[gc][phase_name] = phase_id - gc_start_phase
    return d_gc_phases


def get_gc_minheap(p_support: str, gc: str, config: "yaml.YAMLObject") -> Dict:
    return utils.parse_yaml(get_minheap_path(config, p_support, gc))


def get_base_phase_dict(default_value: Any) -> Dict:
    d_data = dict()
    for phase in BASE_PHASES:
        d_data[phase] = copy.deepcopy(default_value)
    return d_data


def get_phase_dict(default_value: Any, gc_id_to_event_map: Dict) -> Dict:
    d_data = dict()
    for phase in BASE_PHASES:
        d_data[phase] = copy.deepcopy(default_value)
    for phase_key in gc_id_to_event_map.keys():
        if phase_key > 2:
            d_data[gc_id_to_event_map[phase_key]] = copy.deepcopy(default_value)
    return d_data


def get_minheap_path(config: "yaml.YAMLObject", p_support: str, gc: str) -> str:
    if "suite" not in config:
        bm_suite = "dacapo"
    else:
        bm_suite = config["suite"]
    if "size" in config:
        bm_size = config["size"]
    elif "running_size" in config:
        bm_size = config["running_size"]
    else:
        bm_size = "default"
    if "use-lbo-heap" in config["jdk"]:
        b_lbo_heap = config["jdk"]["use-lbo-heap"]
    elif "use_lbo_heap" in config["jdk"]:
        b_lbo_heap = config["jdk"]["use_lbo_heap"]
    else:
        b_lbo_heap = False
    if b_lbo_heap == True:
        return f"{p_support}/min-heap/{bm_suite}/{bm_size}/lbo.yaml"
    else:
        return f"{p_support}/min-heap/{bm_suite}/{bm_size}/{gc}.yaml"


def get_jvm_path(config: "yaml.YAMLObject") -> str:
    # if bool(config["jdk"]["use-client-jdk"]) == True:
    #     return config["jdk"]["path"]["client"]
    return config["jdk"]["counter"]
