import yaml

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List

from common import jvm, utils

BASE_EVENTS = {"OK", "PROCESS", "SAMPLE"}


class Status(Enum):
    UNKNOWN = 1
    DISREGARD = 2
    FAILED = 3
    PASSED = 4
    SKIPPED = 5

    @staticmethod
    def op_and(a: "Status", b: "Status") -> "ColumnType":
        if a == Status.UNKNOWN or b == Status.UNKNOWN:
            return Status.UNKNOWN
        if a == Status.PASSED and b == Status.PASSED:
            return Status.PASSED
        if (a == Status.DISREGARD or a == Status.SKIPPED) and b == Status.PASSED:
            return Status.PASSED
        if a == Status.PASSED and (b == Status.DISREGARD or b == Status.SKIPPED):
            return Status.PASSED
        if a == Status.DISREGARD and b == Status.DISREGARD:
            return Status.DISREGARD
        if a == Status.SKIPPED and b == Status.SKIPPED:
            return Status.SKIPPED
        if a == Status.FAILED or b == Status.FAILED:
            return Status.FAILED
        return Status.FAILED

    @staticmethod
    def from_bool(b: bool) -> "Status":
        if b is True:
            return Status.PASSED
        return Status.FAILED

    @staticmethod
    def yaml_constructor(loader: "yaml.Loader", node: "yaml.Node") -> "Status":
        assert len(node.value) == 1
        value = int(loader.construct_scalar(node.value[0]))
        return Status(value)


class ColumnType(Enum):
    BOOLEAN = 1
    TEXT = 2
    NUMBER = 3

    @staticmethod
    def from_string(s: str) -> "ColumnType":
        if s == "boolean":
            return ColumnType.BOOLEAN
        if s == "number":
            return ColumnType.NUMBER
        if s == "text":
            return ColumnType.TEXT
        assert False

    @staticmethod
    def yaml_constructor(loader: "yaml.Loader", node: "yaml.Node") -> "ColumnType":
        assert len(node.value) == 1
        value = int(loader.construct_scalar(node.value[0]))
        return ColumnType(value)


@dataclass(init=True)
class Column:
    ctype: ColumnType
    cname: str
    ccolor: int
    cgroup: str

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            return self.cname == other
        if isinstance(other, Column):
            return self.cname == other.cname
        raise NotImplementedError

    def __hash__(self) -> int:
        return hash(self.cname)

    @staticmethod
    def yaml_constructor(loader: "yaml.Loader", node: "yaml.Node") -> "Column":
        d_args = dict()
        for node_pair in node.value:
            key = loader.construct_scalar(node_pair[0])
            value = node_pair[1]
            if isinstance(value, yaml.nodes.ScalarNode) == True:
                d_args[key] = loader.construct_scalar(value)
            else:
                d_args[key] = loader.construct_object(value, deep=True)
        return Column(**d_args)


def generate_event_status_dict(p_status: str, skip_execution: bool) -> List:
    y_status = utils.parse_yaml(p_status)
    d_event_status = dict()
    default_value = Status.UNKNOWN
    if skip_execution == True:
        default_value = Status.DISREGARD
    for category in y_status:
        if "events" in y_status[category]:
            for event in y_status[category]["events"]:
                c = Column(
                    ctype=ColumnType.from_string(y_status[category]["events"][event]),
                    cname=event,
                    ccolor=y_status[category]["color"],
                    cgroup=category,
                )
                assert event not in d_event_status
                d_event_status[c] = default_value
        else:
            c = Column(
                ctype=ColumnType.BOOLEAN,
                cname=category,
                ccolor=y_status[category]["color"],
                cgroup=category,
            )
            assert category not in d_event_status
            d_event_status[c] = default_value
    return d_event_status


def check_all_executions(
    d_benchmarks: Dict,
    split_benchmark_path: Callable,
    iterations: int,
) -> Dict:
    for b_hash in d_benchmarks:
        num_ok = 0
        for d_execution in d_benchmarks[b_hash]["EXECUTION"]:
            if d_execution is None:
                continue
            if d_execution["OK"] == Status.SKIPPED:
                continue
            ok_value = Status.DISREGARD
            for event in d_execution.keys():
                if event not in BASE_EVENTS and event.ctype == ColumnType.BOOLEAN:
                    ok_value = Status.op_and(ok_value, d_execution[event])
            d_execution["OK"] = ok_value
            if ok_value == Status.PASSED:
                num_ok += 1
        assert num_ok <= iterations
        if num_ok != iterations:
            d_benchmarks[b_hash]["PROCESS"] = Status.FAILED
            continue
        d_benchmarks[b_hash]["PROCESS"] = Status.PASSED
        for d_execution in d_benchmarks[b_hash]["EXECUTION"]:
            if d_execution is None:
                continue
            if d_execution["OK"] == Status.PASSED:
                d_execution["PROCESS"] = Status.PASSED
    return d_benchmarks


def generate_passed_key_logs_list(
    d_benchmarks: Dict, append_run_path: bool, l_tokens: List[str]
) -> Dict:
    l_passed = list()
    for b_hash in d_benchmarks:
        for idx in range(len(d_benchmarks[b_hash]["EXECUTION"])):
            if d_benchmarks[b_hash]["EXECUTION"][idx] is not None:
                b_tokens_all_pass = True
                for token in l_tokens:
                    if d_benchmarks[b_hash]["EXECUTION"][idx][token] != Status.PASSED:
                        b_tokens_all_pass = False
                if b_tokens_all_pass == True:
                    b_execution = d_benchmarks[b_hash]["PATHS"][idx]
                    if append_run_path == True:
                        l_passed.append(f"{b_execution}_run.log")
                    else:
                        l_passed.append(b_execution)
    return l_passed


def split_events_by_gc(
    l_gc: List, d_benchmarks: Dict, split_benchmark_path: Callable
) -> Dict:
    d_gc_benchmarks = dict()
    for gc in l_gc:
        d_gc_benchmarks[gc] = dict()
    for b_hash in d_benchmarks:
        gc = b_hash.split("_")[1]
        d_gc_benchmarks[gc][b_hash] = set()
        if d_benchmarks[b_hash]["PROCESS"] == Status.PASSED:
            d_gc_benchmarks[gc][b_hash].add("OK")
            continue
        for d_execution in d_benchmarks[b_hash]["EXECUTION"]:
            if d_execution is None:
                continue
            for event in d_execution.keys():
                if (
                    event != "OK"
                    and event != "PROCESS"
                    and event.ctype == ColumnType.BOOLEAN
                ):
                    if d_execution[event] == Status.FAILED:
                        d_gc_benchmarks[gc][b_hash].add(event.cname)
    for gc in d_gc_benchmarks:
        for bm in d_gc_benchmarks[gc]:
            l_gc_error = list(d_gc_benchmarks[gc][bm])
            l_gc_error.sort()
            d_gc_benchmarks[gc][bm] = ", ".join(l_gc_error)
    return d_gc_benchmarks


def generate_check_file(
    p_outdir: str,
    d_benchmarks: Dict,
    split_benchmark_path: Callable,
    l_gc: List,
    append_run_path: bool,
    generate_sample: bool,
) -> None:
    d_output = {
        "OK": generate_passed_key_logs_list(d_benchmarks, append_run_path, ["OK"]),
        "PROCESS": generate_passed_key_logs_list(
            d_benchmarks, append_run_path, ["PROCESS", "OK"]
        ),
        "ALL": list(),
    }
    for b_hash in d_benchmarks:
        for idx in range(len(d_benchmarks[b_hash]["EXECUTION"])):
            b_execution = d_benchmarks[b_hash]["PATHS"][idx]
            if append_run_path == True:
                d_output["ALL"].append(f"{b_execution}_run.log")
            else:
                d_output["ALL"].append(b_execution)
    if l_gc is not None:
        d_gc_benchmarks = split_events_by_gc(l_gc, d_benchmarks, split_benchmark_path)
        d_output["BY_GC"] = d_gc_benchmarks
    if generate_sample == True:
        d_output["SAMPLE"] = generate_passed_key_logs_list(
            d_benchmarks, append_run_path, ["SAMPLE"]
        )
    utils.save_yaml(d_output, f"{p_outdir}/check.yaml")


def get_benchmark_hash(p_execution: str, split_benchmark_path: Callable) -> str:
    bm_name, bm_gc, _, bm_heap = split_benchmark_path(p_execution)
    if bm_gc is None:
        return bm_name
    else:
        return f"{bm_name}_{bm_gc}"


def drop_benchmark_heap_from_hash(b_hash: str) -> str:
    return "_".join(b_hash.split("_")[:-1])


def generate_execution_dict(
    l_expected_logs: str, max_attempts: int, split_benchmark_path: Callable
) -> Dict:
    d_benchmarks = dict()
    for p_execution in l_expected_logs:
        b_hash = get_benchmark_hash(p_execution, split_benchmark_path)
        if b_hash not in d_benchmarks:
            d_benchmarks[b_hash] = {
                "EXECUTION": [None] * max_attempts,
                "PROCESS": Status.UNKNOWN,
                "PATHS": [None] * max_attempts,
            }
    return d_benchmarks


def check_correct_heap(
    d_event_state: Dict,
    config: "yaml.YAMLObject",
    p_support: str,
    p_benchmark: str,
    split_benchmark_path: Callable,
) -> Dict:
    bm_name, bm_gc, _, bm_heap = split_benchmark_path(p_benchmark)
    bm_minheap = jvm.get_gc_minheap(p_support, bm_gc, config)[bm_name]
    bm_expected_heap = round(bm_minheap * config["jdk"]["heap-multiplier"])
    d_event_state["CORRECT_HEAP"] = Status.from_bool(int(bm_heap) == bm_expected_heap)
    return d_event_state
