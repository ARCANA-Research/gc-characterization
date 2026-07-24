import copy
import os
import shutil
import socket
import subprocess
import sys

from typing import Dict

sys.path.append(os.path.abspath("support"))
from common import jvm, utils


def setup_tokens(config: "yaml.YAMLObject", p_output: str, p_curr: str) -> Dict:
    if config["jdk"]["use-lbo-heap"] == True:
        jdk_heap = f"same_heap_{int(config['jdk']['heap-multiplier'])}x"
    else:
        jdk_heap = "min_heap"
    return {
        "BUILDPATH": "/benchmark/build",
        "BENCHMARKS": config["benchmark"],
        "JDKPATH": "/benchmark/jdk",
        "DACAPOPATH": "/benchmark/dacapo-23.11-MR2-chopin.jar",
        "JDKVERSION": config["jdk"]["version"],
        "MINHEAPMULTIPLIER": config["jdk"]["heap-multiplier"],
        "JVMCORECOUNT": config["jdk"]["num-cpus"],
        "CURRDIR": p_curr,
        "JDKHEAP": jdk_heap,
        "RUNS": config[config["suite"]]["runs"],
        "SIZE": config["size"],
        "JFRPATH": "/benchmark/jfr",
    }


def create_dryrun(
    gc: str, p_running_dir: str, p_running_config: str, p_running_output: str
) -> None:
    f_log = open(p_running_output, "a")
    p = subprocess.run(
        ["running", "-d", "runbms", p_running_dir, p_running_config, "-s", "1"],
        stdout=f_log,
        stderr=f_log,
    )
    f_log.close()


def main():
    config = utils.parse_yaml("config.yaml")
    p_curr = utils.get_currdir()
    p_support = f"{p_curr}/support"
    p_output, _ = utils.create_output_folder(
        config["out"]["path"], None, config["benchmark"]
    )
    p_running = f"{p_output}/running"
    os.makedirs(p_running)
    p_running_configs = f"{p_running}/configs"
    os.makedirs(p_running_configs)
    p_running_dry_runs = f"{p_running}/dryrun"
    os.makedirs(p_running_dry_runs)
    shutil.copytree(f"{p_curr}/config", f"{p_output}/config")
    utils.save_yaml(
        utils.parse_yaml(f"{p_support}/simulator/command.yaml"),
        f"{p_output}/command.yaml",
    )
    shutil.copyfile(f"{p_support}/eventmap.yaml", f"{p_output}/eventmap.yaml")
    running_ng_config = utils.parse_yaml(
        f"{p_curr}/running/simulator/{config['suite']}.yaml"
    )
    base_tokens = setup_tokens(config, p_output, p_curr)
    base_tokens["OUTDIR"] = p_output
    for gc in config["gc"]:
        tokens = copy.deepcopy(base_tokens)
        tokens["GC"] = gc
        tokens["BMSIZE"] = config["size"]
        p_minheap = jvm.get_minheap_path(config, p_support, gc)
        tokens["MINHEAP"] = utils.parse_yaml(p_minheap)
        gc_config = utils.dict_replace_tokens(copy.deepcopy(running_ng_config), tokens)
        p_running_gc_config = f"{p_running_configs}/{gc}.yaml"
        utils.save_yaml(gc_config, p_running_gc_config)
    utils.move_config_includes(p_running_configs, base_tokens)
    for gc in config["gc"]:
        p_running_gc_config = f"{p_running_configs}/{gc}.yaml"
        p_running_output = f"{p_running_dry_runs}/{gc}.log"
        create_dryrun(gc, p_running, p_running_gc_config, p_running_output)
    utils.save_yaml(config, f"{p_output}/config.yaml")
    print(p_output)


if __name__ == "__main__":
    main()
