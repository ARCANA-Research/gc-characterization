import subprocess

from datetime import datetime
from common import parallelize, utils


def execute_benchmark(cmd: str, p_base: str) -> None:
    cmd = cmd.strip()
    p_runlog = f"{p_base}/run.log"
    f_runlog = open(p_runlog, "w")
    curr_time = datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
    f_runlog.write(f"START TIME: {curr_time}\n")
    f_runlog.flush()
    subprocess.run(cmd, stdout=f_runlog, stderr=f_runlog)
    curr_time = datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
    f_runlog.write(f"END TIME: {curr_time}\n")
    f_runlog.flush()
    f_runlog.close()


def get_benchmark_base_path(p_cmd: str) -> str:
    return p_cmd[: p_cmd.rfind("/", 0, p_cmd.rfind("/"))]


def execute_parallel_scripts(parallel_executions: int, p_cmds: str) -> None:
    f_cmds = open(p_cmds, "r")
    p_list = list()
    l_args = list()
    for idx, cmd in enumerate(f_cmds):
        l_args.append({"cmd": cmd, "p_base": get_benchmark_base_path(cmd)})
    parallelize.parallelize_base(parallel_executions, execute_benchmark, l_args)


def execute_condor(p_condir_shell: str) -> None:
    p = subprocess.run([p_condir_shell])


def execute_benchmarks(p_output: str, parallel_executions: int) -> None:
    execute_parallel_scripts(parallel_executions, f"{p_output}/commands/scripts.log")


if __name__ == "__main__":
    main()
