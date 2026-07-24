import os
import socket
import subprocess
import threading

from typing import Callable, List

from common import progress

progress_bar = None

execution_contexts = None

execution_method = None
execution_args = None

execution_position = None
execution_position_mutex = None


def execute_subprocess(cmd: str, p_log: str) -> None:
    if p_log is not None:
        f_log = open(p_log, "a")
        subprocess.run(cmd.split(), stdout=f_log, stderr=f_log, check=True)
        f_log.close()
    else:
        subprocess.run(cmd.split(), check=True)


def execution_thread(tid: int) -> None:
    global progress_bar
    global execution_method
    global execution_args
    global execution_position
    global execution_position_mutex
    next_command_position = None
    with execution_position_mutex:
        next_command_position = execution_position
        execution_position += 1
    while next_command_position < len(execution_args):
        progress.advance(progress_bar)
        execution_method(**execution_args[next_command_position])
        progress.advance(progress_bar)
        with execution_position_mutex:
            next_command_position = execution_position
            execution_position += 1


def parallelize_base(
    num_parallel: int, parallel_method: Callable, l_args: List
) -> None:
    global progress_bar
    global execution_contexts
    global execution_method
    global execution_args
    global execution_position
    global execution_position_mutex
    # initialize variables
    execution_contexts = [None] * num_parallel
    execution_position = 0
    execution_position_mutex = threading.Lock()
    execution_args = list()
    # build dictionary of subprocess arguments
    execution_method = parallel_method
    execution_args = l_args
    # start threads
    progress_bar = progress.start(f"Parallel Execution", len(execution_args) * 2)
    num_threads = num_parallel
    if num_parallel > len(execution_args):
        num_threads = len(execution_args)
    for tid in range(num_threads):
        execution_contexts[tid] = threading.Thread(target=execution_thread, args=[tid])
        execution_contexts[tid].start()
        assert execution_contexts[tid].is_alive()
    for tid in range(num_threads):
        execution_contexts[tid].join()
        execution_contexts[tid] = None
    progress.end(progress_bar)


def num_cpus() -> int:
    return os.cpu_count()
