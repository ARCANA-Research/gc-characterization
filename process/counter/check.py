import argparse
import os
import regex
import sys

from typing import Callable, Dict, List
from yaml.representer import Representer

sys.path.append(os.path.abspath("support"))
from common import check, check_table, jfr, jvm, progress, utils
from common.counter import counterexec, check_utils


def get_execution_time(p_benchmark: str) -> Dict:
    f_benchmark = open(f"{p_benchmark}_run.log", "r")
    execution_time = -1
    for line in f_benchmark:
        if "EXECUTION TIME" in line:
            return float(line.split()[-1])
    return None


def check_agent_pid(p_run: str, p_verify: str) -> bool:
    if os.path.isfile(p_run) == False:
        return check.Status.FAILED
    runlog_pid = -1
    verifylog_pid = -2
    with utils.CommonFile(p_run, "r") as run_log:
        for i, log_line in enumerate(run_log):
            if "AGENT PID" in log_line:
                runlog_pid = int(log_line.split()[-1])
                break
    y_verify = utils.parse_yaml(p_verify)
    verifylog_pid = int(y_verify["agent_pid"])
    return check.Status.from_bool(runlog_pid == verifylog_pid)


def generate_skipped_execution_logs(
    p_outdir: str,
    max_attempts: int,
    l_expected_logs: List[str],
) -> List:
    return check_utils.get_logs_by_runing_ng_state_filter(
        p_outdir, max_attempts, l_expected_logs, check_utils.RunningStatus.SKIPPED
    )


def generate_passed_execution_logs(
    p_outdir: str,
    max_attempts: int,
    l_expected_logs: List[str],
) -> List:
    return check_utils.get_logs_by_runing_ng_state_filter(
        p_outdir, max_attempts, l_expected_logs, check_utils.RunningStatus.PASSED
    )


def get_gc_name(p_benchmark_log: str) -> str:
    return p_benchmark_log.split("/")[-1].split("_")[0]


def check_threads_measured(p_perf: str, p_verify: str, key: str) -> "check.Status":
    l_verify_tids = list()
    l_ignored_threads = list()
    p_run = p_perf.replace("perf", "run")
    with utils.CommonFile(p_run, "r") as f_run:
        for line in f_run:
            if "THREAD START IGNORED" in line:
                l_ignored_threads.append(int(line.split()[-1]))
    y_verify = utils.parse_yaml(p_verify)
    if y_verify["threads"] is None:
        print("Check: Disregarding threads")
        return check.Status.DISREGARD
    for thread in y_verify["threads"]:
        if thread["type"] == key:
            thread_tid = int(thread["tid"])
            if thread_tid not in l_ignored_threads:
                l_verify_tids.append(thread_tid)
    y_perf = utils.parse_yaml(p_perf)
    if y_perf["AGENT"][f"{key}_THREAD_COUNT"] < len(l_verify_tids):
        return check.Status.FAILED
    l_perf_tids = list(y_perf["AGENT"][f"{key}_THREADS"])
    for verify_tid in l_verify_tids:
        if verify_tid not in l_perf_tids:
            return check.Status.FAILED
    return check.Status.PASSED


def check_gc_threads_measured(
    p_perf: str, p_verify: str, d_execution_params: Dict
) -> "check.Status":
    if d_execution_params[counterexec.ExecutionParams.CONCURRENT_GC] is False:
        return check.Status.DISREGARD
    if os.path.isfile(p_perf) == False:
        return check.Status.FAILED
    return check_threads_measured(p_perf, p_verify, "GC")


def check_jvm_threads_measured(
    p_perf: str, p_verify: str, d_execution_params: Dict
) -> "check.Status":
    if d_execution_params[counterexec.ExecutionParams.PER_THREAD_MEASUREMENT] is False:
        return check.Status.DISREGARD
    if os.path.isfile(p_perf) == False:
        return check.Status.FAILED
    return check_threads_measured(p_perf, p_verify, "JVM")


def check_if_valid_events(l_events: List[int], y_perf: "yaml.YAMLObject") -> bool:
    if "total" in y_perf:
        y_perf = y_perf["total"]
    for idx, val in enumerate(y_perf):
        if val > 0:
            if idx not in l_events:
                return False
    return True


def check_perf_file_agent_validity(
    p_perf: str, p_eventmap: str, d_execution_params: Dict
) -> "check.State":
    gc = get_gc_name(p_perf)
    counter_gc_events = d_execution_params[counterexec.ExecutionParams.COUNTER_EVENTS]
    default_gc_events = not counter_gc_events
    l_events, _, _ = jvm.valid_phases(
        p_eventmap, gc, counter_gc_events, default_gc_events
    )
    y_perf = utils.parse_yaml(p_perf)
    if check_if_valid_events(l_events, y_perf["AGENT"]["GC_EVENT_COUNT"]) is False:
        return check.Status.FAILED
    if check_if_valid_events(l_events, y_perf["AGENT"]["TIME"]) is False:
        return check.Status.FAILED
    return check.Status.PASSED


def check_perf_file_perf_validity(
    p_perf: str, p_eventmap: str, d_execution_params: Dict
) -> "check.State":
    gc = get_gc_name(p_perf)
    counter_gc_events = d_execution_params[counterexec.ExecutionParams.COUNTER_EVENTS]
    default_gc_events = not counter_gc_events
    l_events, _, _ = jvm.valid_phases(
        p_eventmap, gc, counter_gc_events, default_gc_events
    )
    y_perf = utils.parse_yaml(p_perf)
    if d_execution_params[counterexec.ExecutionParams.PERF_COUNTERS] is False:
        return check.Status.DISREGARD
    if "GC" not in y_perf or "JVM" not in y_perf:
        return check.Status.FAILED
    for event in y_perf["JVM"]:
        if d_execution_params[counterexec.ExecutionParams.CONCURRENT_GC] is True:
            if check_if_valid_events(l_events, y_perf["GC"][event]) is False:
                return check.Status.FAILED
        if check_if_valid_events(l_events, y_perf["JVM"][event]) is False:
            return check.Status.FAILED
    return check.Status.PASSED


def check_jvm_gc_events_same(p_perf: str, d_execution_params: Dict) -> bool:
    if d_execution_params[counterexec.ExecutionParams.PERF_COUNTERS] is False:
        return check.Status.DISREGARD
    if d_execution_params[counterexec.ExecutionParams.CONCURRENT_GC] is False:
        return check.Status.DISREGARD
    y_perf = utils.parse_yaml(p_perf)
    return check.Status.from_bool(list(y_perf["GC"]) == list(y_perf["JVM"]))


def check_run_log_file(
    p_benchmark: str,
    d_event_state: Dict,
    agent_type: str,
    d_execution_params: Dict,
    l_passed_logs: List[str],
) -> List:
    p_run = f"{p_benchmark}_run.log"
    b_found_log_file = os.path.isfile(p_run)
    d_event_state["LOG_FOUND"] = check.Status.from_bool(b_found_log_file)
    if b_found_log_file == False:
        return d_event_state
    log_check = utils.check_file_has_strings(
        p_run,
        [
            "PASSED in",
            "Validation FAILED",
            ".OutOfMemoryError",
            "ERROR ->",
            "SUBPROCESS TIMEOUT",
            "multiplexed",
            "ASSERT FAILED:",
        ],
    )
    b_found_passed = log_check[0]
    b_found_validation_failed = log_check[1]
    b_found_out_of_memory = log_check[2]
    b_found_subprocess_error = log_check[3]
    b_found_subprocess_timeout = log_check[4]
    b_found_counter_multiplexed = log_check[5]
    b_found_assert_failed = log_check[6]
    b_found_passed = p_benchmark in l_passed_logs
    d_event_state["PASSED"] = check.Status.from_bool(b_found_passed)
    d_event_state["VALIDATION_PASSED"] = check.Status.from_bool(
        not b_found_validation_failed
    )
    d_event_state["NO_OUT_OF_MEMORY"] = check.Status.from_bool(
        not b_found_out_of_memory
    )
    d_event_state["SUBPROCESS_ERROR"] = check.Status.from_bool(
        not b_found_subprocess_error
    )
    d_event_state["NO_TIMEOUT"] = check.Status.from_bool(not b_found_subprocess_timeout)
    d_event_state["COUNTER_MULTIPLEXED"] = check.Status.from_bool(
        not b_found_counter_multiplexed
    )
    d_event_state["ASSERT_FAILED"] = check.Status.from_bool(not b_found_assert_failed)
    d_event_state["EXECUTION_TIME"] = get_execution_time(p_benchmark)
    d_event_state["EXECUTION_PATH"] = p_benchmark
    d_event_state["CORRECT_AGENT_USED"] = check.Status.from_bool(
        agent_type.upper()
        == d_execution_params[counterexec.ExecutionParams.TYPE].upper()
    )
    return d_event_state


def check_perf_file(
    p_benchmark: str,
    p_outdir: str,
    p_eventmap: str,
    d_execution_params: Dict,
    d_event_state: Dict,
) -> List:
    p_perf = f"{p_benchmark}_perf.log"
    b_found_perf_file = os.path.isfile(p_perf)
    d_event_state["PERF_FOUND"] = check.Status.from_bool(b_found_perf_file)
    if b_found_perf_file == False:
        return d_event_state
    d_event_state["CORRECT_AGENT_COUNTERS"] = check_perf_file_agent_validity(
        p_perf, p_eventmap, d_execution_params
    )
    d_event_state["CORRECT_PERF_COUNTERS"] = check_perf_file_perf_validity(
        p_perf, p_eventmap, d_execution_params
    )
    d_event_state["SAME_GC_JVM_EVENTS"] = check_jvm_gc_events_same(
        p_perf, d_execution_params
    )
    return d_event_state


def check_jvm_error_file(p_benchmark: str, d_event_state: Dict) -> List:
    p_jvm_error_log = f"{p_benchmark}_error.log"
    b_found_error_file = os.path.isfile(p_jvm_error_log)
    d_event_state["JVM_ERROR_DUMP_NOT_FOUND"] = check.Status.from_bool(
        not b_found_error_file
    )
    return d_event_state


def check_verify_file(
    p_benchmark: str,
    d_execution_params: Dict,
    d_event_state: Dict,
) -> List:
    p_verify = f"{p_benchmark}_verify.yaml"
    b_found_verify_file = os.path.isfile(p_verify)
    d_event_state["VERIFY_FOUND"] = check.Status.from_bool(b_found_verify_file)
    if b_found_verify_file == False:
        return d_event_state
    y_verify = utils.parse_yaml(p_verify)
    d_event_state["EXECUTION_VERIFIED"] = check.Status.from_bool(y_verify["passed"])
    p_run = f"{p_benchmark}_run.log"
    d_event_state["PID_CONSISTENT"] = check_agent_pid(p_run, p_verify)
    p_perf = f"{p_benchmark}_perf.log"
    d_event_state["CONSISTENT_GC_THREADS"] = check_gc_threads_measured(
        p_perf, p_verify, d_execution_params
    )
    d_event_state["CONSISTENT_JVM_THREADS"] = check_jvm_threads_measured(
        p_perf, p_verify, d_execution_params
    )
    return d_event_state


def check_jfr(p_benchmark: str, d_event_state: Dict, config: "yaml.YAMLObject") -> List:
    p_run = f"{p_benchmark}_run.log"
    if os.path.isfile(p_run) == False:
        return d_event_state
    log_check = utils.check_file_has_strings(
        p_run,
        [
            "[jfr",
        ],
    )
    p_jfr = f"{p_benchmark}.jfr"
    if log_check[0] == True:
        if os.path.isfile(p_jfr) == False:
            d_event_state["ROI_MARKER"] = check.Status.FAILED
            return d_event_state
    else:
        if os.path.isfile(p_jfr) == True:
            d_event_state["ROI_MARKER"] = check.Status.FAILED
            return d_event_state
        else:
            d_event_state["ROI_MARKER"] = check.Status.DISREGARD
            return d_event_state
    if d_event_state["PASSED"] != check.Status.PASSED:
        return d_event_state
    d_event_state["ROI_MARKER"] = check.Status.from_bool(
        jfr.check_jfr_roi_markers(config, p_jfr)
    )
    return d_event_state


def generate_events(
    p_outdir: str,
    p_support: str,
    p_eventmap: str,
    l_expected_logs: List[str],
    l_skipped_logs: List[str],
    l_passed_logs: List[str],
    p_status: str,
    agent_type: str,
    max_attempts: int,
    split_benchmark_path: Callable,
    config: "yaml.YAMLObject",
) -> Dict:
    d_benchmarks = check.generate_execution_dict(
        l_expected_logs, max_attempts, split_benchmark_path
    )
    progress_bar = progress.start(f"Checking", len(l_expected_logs))
    config = utils.parse_yaml(f"{p_outdir}/config.yaml")
    for p_benchmark in l_expected_logs:
        print(f"Checking -> {p_benchmark}")
        d_event_state = False
        if p_benchmark in l_skipped_logs:
            d_event_state = check.generate_event_status_dict(p_status, True)
        else:
            d_execution_params = counterexec.parse_execution_params(
                f"{p_benchmark}_run.log"
            )
            d_event_state = check.generate_event_status_dict(p_status, False)
            d_event_state = check.check_correct_heap(
                d_event_state, config, p_support, p_benchmark, split_benchmark_path
            )
            d_event_state = check_run_log_file(
                p_benchmark,
                d_event_state,
                agent_type,
                d_execution_params,
                l_passed_logs,
            )
            d_event_state = check_perf_file(
                p_benchmark,
                p_outdir,
                p_eventmap,
                d_execution_params,
                d_event_state,
            )
            d_event_state = check_jvm_error_file(p_benchmark, d_event_state)
            d_event_state = check_verify_file(
                p_benchmark,
                d_execution_params,
                d_event_state,
            )
            d_event_state = check_jfr(p_benchmark, d_event_state, config)
        b_hash = check.get_benchmark_hash(p_benchmark, split_benchmark_path)
        _, _, bm_iteration, _ = split_benchmark_path(p_benchmark)
        d_benchmarks[b_hash]["EXECUTION"][bm_iteration] = d_event_state
        d_benchmarks[b_hash]["PATHS"][bm_iteration] = p_benchmark
        progress.advance(progress_bar)
    progress.end(progress_bar)
    return d_benchmarks


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--outdir", required=True, nargs=1)
    args = parser.parse_args()
    p_outdir = args.outdir[0]
    p_eventmap = f"{p_outdir}/eventmap.yaml"
    p_support = f"{utils.get_currdir()}/support"
    p_status = f"{p_support}/counter/statusmap.yaml"
    config = utils.parse_yaml(f"{p_outdir}/config.yaml")
    max_attempts = config["counter"]["max-attempts"]
    iterations = config["counter"]["iterations"]
    l_expected_logs = check_utils.generate_expected_execution_logs(p_outdir)
    l_skipped_logs = generate_skipped_execution_logs(
        p_outdir, max_attempts, l_expected_logs
    )
    l_passed_logs = generate_passed_execution_logs(
        p_outdir, max_attempts, l_expected_logs
    )
    d_benchmarks = generate_events(
        p_outdir,
        p_support,
        p_eventmap,
        l_expected_logs,
        l_skipped_logs,
        l_passed_logs,
        p_status,
        config["counter"]["agent"],
        max_attempts,
        counterexec.split_benchmark_path,
        config,
    )
    d_benchmarks = check.check_all_executions(
        d_benchmarks, counterexec.split_benchmark_path, iterations
    )
    check.generate_check_file(
        p_outdir,
        d_benchmarks,
        counterexec.split_benchmark_path,
        config["gc"],
        True,
        False,
    )
    table = check_table.generate_table(
        d_benchmarks, p_status, counterexec.split_benchmark_path, True, iterations
    )
    utils.save_yaml(d_benchmarks, f"{p_outdir}/check_table.yaml")
    utils.write_to_file(table, f"{p_outdir}/check.ansi")


if __name__ == "__main__":
    main()
