import regex

from enum import Enum
from typing import Dict, List

from common import utils
from common.counter import counterexec

MINHEAP_NOT_SET_REGEX = regex.compile(
    r".*\[WARNING\].*Minheap for (\w+) of Benchmark Suite .* not set"
)


class RunningStatus(Enum):
    PASSED = "[passed -> a]"
    SKIPPED = "."
    OOM_ERROR = "[oom,error]"
    FAILED = "[failed]"
    TIMEOUT = "[timeout]"
    VALIDATION_ERROR = "[validation failed,error]"

    @staticmethod
    def from_run_log(line: str, run_attempt: int) -> "RunningStatus":
        for running_status in RunningStatus:
            expected_string = f"{run_attempt}{running_status.value}"
            if expected_string in line:
                return running_status
        print(f"CHECKERROR: Running Status Not Found -> {line}")
        assert False

    @staticmethod
    def generate_run_list(line: str, max_attempts: int) -> List["RunningStatus"]:
        l_status = [None] * max_attempts
        for run_attempt in range(max_attempts):
            l_status[run_attempt] = RunningStatus.from_run_log(line, run_attempt)
        return l_status

    @staticmethod
    def generate_skip_list(max_attempts: int) -> List["RunningStatus"]:
        l_status = [None] * max_attempts
        for run_attempt in range(max_attempts):
            l_status[run_attempt] = RunningStatus.SKIPPED
        return l_status


def get_logs_by_runing_ng_state_filter(
    p_outdir: str,
    max_attempts: int,
    l_expected_logs: List[str],
    filter_key: "RunningStatus",
) -> List:
    d_status = get_logs_by_runing_ng_state(f"{p_outdir}/run.log", max_attempts)
    l_logs = list()
    for p_benchmark in l_expected_logs:
        bm_name, bm_gc, bm_iteration, bm_heap = counterexec.split_benchmark_path(
            p_benchmark
        )
        bm_tuple = (bm_name, bm_heap)
        assert bm_tuple in d_status[bm_gc]
        if d_status[bm_gc][bm_tuple][bm_iteration] == filter_key:
            l_logs.append(p_benchmark)
    return l_logs


def get_logs_by_runing_ng_state(p_run: str, max_attempts: int) -> List:
    d_status = dict()
    with utils.CommonFile(p_run, "r") as f_run:
        current_gc = None
        skipped_bm = None
        is_run_log = False
        for line in f_run:
            if "STARTING ->" in line:
                current_gc = line.split()[-1]
                assert current_gc not in d_status
                d_status[current_gc] = dict()
                skipped_bm = set()
                is_run_log = False
            elif "FINISHED ->" in line:
                is_run_log = False
                skipped_bm = None
            elif "Run id:" in line:
                is_run_log = True
            elif is_run_log is True:
                line_split = line.split()
                if len(line_split) == 0:
                    continue
                bm_name = line_split[0]
                bm_heap = int(line_split[2])
                bm_tuple = (bm_name, bm_heap)
                assert bm_tuple not in d_status[current_gc]
                if bm_name in skipped_bm:
                    d_status[current_gc][bm_tuple] = RunningStatus.generate_skip_list(
                        max_attempts
                    )
                else:
                    d_status[current_gc][bm_tuple] = RunningStatus.generate_run_list(
                        line, max_attempts
                    )
                l_bms = utils.get_regex_matches(line, MINHEAP_NOT_SET_REGEX)
                if l_bms is not None and len(l_bms) > 0:
                    assert len(l_bms) == 1
                    skipped_bm.add(l_bms[0])
    return d_status


def generate_expected_execution_logs(p_outdir: str) -> List:
    p_dryrun = f"{p_outdir}/dry.log"
    p_config = f"{p_outdir}/config.yaml"
    y_config = utils.parse_yaml(p_config)
    num_expected_logs = (
        len(y_config["benchmark"])
        * len(y_config["gc"])
        * y_config["counter"]["max-attempts"]
    )
    l_expected_log_files = list()
    s_hash = set()
    with utils.CommonFile(p_dryrun, "r") as f_dryrun:
        for line in f_dryrun:
            if "LD_PRELOAD" in line:
                # num_expected_logs += 1
                line_split = line.split()
                for line_part in line_split:
                    if "COUNTER_STATS_FILE" in line_part:
                        line_part = line_part.split("=")[-1][1:-1]
                        line_part = line_part.replace("_perf.log", "")
                        p_execution = "/".join(line_part.split("/")[-2:])
                        p_log = f"{p_outdir}/{p_execution}"
                        (
                            bm_name,
                            bm_gc,
                            bm_iteration,
                            bm_heap,
                        ) = counterexec.split_benchmark_path(p_log)
                        b_hash = f"{bm_name}_{bm_gc}"
                        if b_hash not in s_hash:
                            s_hash.add(b_hash)
                            for i in range(y_config["counter"]["max-attempts"]):
                                p_execution_iter = p_execution.replace(
                                    f"{bm_gc}_0_", f"{bm_gc}_{i}_"
                                )
                                l_expected_log_files.append(
                                    f"{p_outdir}/{p_execution_iter}"
                                )
                        break
    assert num_expected_logs == len(l_expected_log_files)
    return l_expected_log_files


def save_run_status_dict(d_status: Dict, p_run: str) -> None:
    with utils.CommonFile(p_run, "w") as f_run:
        for bm_gc in d_status:
            f_run.write(f"STARTING -> {bm_gc}\nRun id: Merged\n")
            for bm_tuple in d_status[bm_gc]:
                f_run.write(f"{bm_tuple[0]} Merged {bm_tuple[1]} ")
                for bm_iteration, bm_status in enumerate(d_status[bm_gc][bm_tuple]):
                    f_run.write(f"{bm_iteration}{bm_status.value}")
                f_run.write("\n")
            f_run.write(f"FINISHED -> {bm_gc}\n")
