import argparse
import os
import re
import socket
import stat
import sys

from collections import defaultdict
from typing import Dict, List

sys.path.append(os.path.abspath("support"))
from common import utils


def get_and_remove_jvm_arg(log_line: str, arg_name: str) -> str:
    assert arg_name in log_line
    log_line = log_line.replace('"', "")
    arg_matches = list(re.finditer(arg_name + r"=[\S]+", log_line))
    assert len(arg_matches) == 1
    arg_value = arg_matches[0].group(0)
    arg_value = arg_value[arg_value.rfind("=") + 1 :]
    log_line = log_line.replace(arg_matches[0].group(0), "")
    log_line = log_line.replace("  ", " ")
    log_line = log_line.strip()
    return arg_value, log_line


def parse_commands(p_outdir: str) -> Dict[str, str]:
    y_command = utils.parse_yaml(f"{p_outdir}/command.yaml")
    d_command = dict()
    for binary in y_command.keys():
        d_binary = y_command[binary]
        cmd_binary = d_binary["command"]
        for cmd_arg in d_binary["args"]:
            cmd_binary += f" {cmd_arg}"
        d_command[binary] = cmd_binary
    return d_command


def parse_benchmark_path(p_dryrun: str, p_outdir: str) -> List[Dict[str, str]]:
    l_cmds = list()
    f_dryrun = open(p_dryrun, "r")
    for log_line in f_dryrun:
        if "exec_path" in log_line:
            p_execution, log_line = get_and_remove_jvm_arg(log_line, "exec_path")
            p_relative, log_line = get_and_remove_jvm_arg(log_line, "relative_path")
            p_checkpoint, log_line = get_and_remove_jvm_arg(log_line, "checkpoint_path")
            l_cmds.append(
                {
                    "jvm_cmd": log_line,
                    "execution": p_execution,
                    "relative": p_relative,
                    "checkpoint": p_checkpoint,
                    "local": f"{p_outdir}/{p_relative}",
                }
            )
    f_dryrun.close()
    return l_cmds


def generate_execution_command(config: "yaml.YAMLObject", d_commands: Dict) -> str:
    return d_commands["gem5"] + " " + d_commands["gem5-config"]


def generate_debug_tokens(
    config: "yaml.YAMLObject",
    s_cmd: str,
    d_def: Dict,
    p_outdir: str,
    bm_gc: str,
    p_curr: str,
) -> Dict:
    p_deps = f"{p_curr}/deps"
    p_support = f"{p_curr}/support/simulator"
    tokens = {
        "OUTDIR": p_outdir,
        "LOCALOUTDIR": p_outdir,
        "BENCHMARKDIR": d_def["execution"],
        "SIMBINARY": f"{p_deps}/gem5/build/X86/gem5.fast",
        "SIMCONFIGDIR": f"{p_outdir}/config",
        "DRAMCONFIG": f"{p_outdir}/config/DDR4.yaml",
        "BENCHMARKIMAGE": f"{p_deps}/benchmark.img",
        "UBUNTUIMAGE": f"{p_deps}/x86-ubuntu-22.04",
        "KERNELPATH": f"{p_support}/linux/vmlinux",
    }
    return tokens


def create_command_scripts(
    config: "yaml.YAMLObject",
    d_def: Dict,
    d_commands: Dict,
    p_outdir: str,
    bm_gc: str,
    p_curr: str,
) -> None:
    p_cmddir = f"{d_def['local']}/scripts"
    os.makedirs(p_cmddir)
    p_jvm_cmd = f"{p_cmddir}/jvm_cmd.log"
    f_jvm_cmd = open(p_jvm_cmd, "w")
    f_jvm_cmd.write(f"{d_def['jvm_cmd']}")
    f_jvm_cmd.close()
    s_execution_cmd = generate_execution_command(config, d_commands)
    execution_tokens = generate_debug_tokens(
        config, s_execution_cmd, d_def, p_outdir, bm_gc, p_curr
    )
    shell_cmd = utils.str_replace_tokens(s_execution_cmd, execution_tokens)
    p_execution_cmd = f"{p_cmddir}/execution.sh"
    f_execution_cmd = open(p_execution_cmd, "w")
    f_execution_cmd.write(f"#! /bin/bash\n")
    f_execution_cmd.write(f"{shell_cmd}\n")
    f_execution_cmd.close()
    utils.make_shell_executable(p_execution_cmd)
    return p_execution_cmd


def create_execution_log(p_cmds: str, l_executions: List) -> None:
    f_cmds = open(p_cmds, "w")
    for p_execution in l_executions:
        f_cmds.write(f"{p_execution}/scripts/execution.sh\n")
    f_cmds.close()


def create_execution_commands(
    config: "yaml.YAMLObject", p_outdir: str, l_executions: List[str]
) -> None:
    p_command_dir = f"{p_outdir}/commands"
    os.makedirs(p_command_dir)
    create_execution_log(f"{p_command_dir}/scripts.log", l_executions)


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--outdir", required=True, nargs=1)
    args = parser.parse_args()
    p_outdir = args.outdir[0]
    p_curr = utils.get_currdir()
    config = utils.parse_yaml(f"{p_outdir}/config.yaml")
    d_commands = parse_commands(p_outdir)
    l_executions = list()
    for gc in config["gc"]:
        l_defs = parse_benchmark_path(f"{p_outdir}/running/dryrun/{gc}.log", p_outdir)
        assert len(l_defs) == len(config["benchmark"])
        for d_def in l_defs:
            os.makedirs(d_def["local"])
            bm_heap = int(d_def["relative"].split("/")[-1].split("_")[-1])
            if bm_heap >= config["simulator"]["maximum-heap"]:
                continue
            p_execution_script = create_command_scripts(
                config, d_def, d_commands, p_outdir, gc, p_curr
            )
            l_executions.append(d_def["local"])
    create_execution_commands(config, p_outdir, l_executions)


if __name__ == "__main__":
    main()
