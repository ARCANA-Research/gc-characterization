import argparse
import logging
import os
import subprocess
import sys

from typing import List

sys.path.append(os.path.abspath("support"))
from common import utils, progress


def get_running_ng_command(gc: str, p_out: str, config: "yaml.YAMLObject") -> List[str]:
    p_running = f"{p_out}/running"
    p_running_config = f"{p_running}/configs/{gc}.yaml"
    l_cmd = ["runbms", p_running, p_running_config, "-s", config["running-ng"]["slice"]]
    if "flags" in config["running-ng"]:
        for flag in config["running-ng"]["flags"]:
            l_cmd += flag.split()
    l_dry = ["running", "-d"] + l_cmd
    l_running = ["running"] + l_cmd
    if "prepend" in config["running-ng"]:
        l_prepend = config["running-ng"]["prepend"].split()
        l_dry = l_prepend + l_dry
        l_running = l_prepend + l_running
    l_dry = [str(arg) for arg in l_dry]
    l_running = [str(arg) for arg in l_running]
    return l_dry, l_running


def execute_gc(gc: str, p_out: str, p_artifact: str, config: "yaml.YAMLObject") -> None:
    f_run = open(f"{p_out}/run.log", "a")
    l_dry, l_running = get_running_ng_command(gc, p_out, config)
    f_dry = open(f"{p_out}/dry.log", "a")
    p_dry = subprocess.run(l_dry, stdout=f_dry, stderr=f_dry)
    f_dry.close()
    str_running = " ".join(l_running)
    logging.info(f"STARTING -> {gc}")
    logging.info(f"CMD -> {str_running}")
    p_running = subprocess.run(l_running, stdout=f_run, stderr=f_run)
    logging.info(f"FINISHED -> {gc}")
    f_run.close()


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--outdir", required=True, nargs=1)
    args = parser.parse_args()
    p_out = args.outdir[0]
    p_artifact = utils.get_currdir()
    config = utils.parse_yaml(f"{p_out}/config.yaml")

    logging.basicConfig(
        filename=f"{p_out}/run.log",
        filemode="a",
        format="[%(asctime)s] %(levelname)-5s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y.%m.%d_%H.%M.%S",
    )

    progress_bar = progress.start(f"Executing", len(config["gc"]))
    for gc in config["gc"]:
        execute_gc(gc, p_out, p_artifact, config)
        progress.advance(progress_bar)
    progress.end(progress_bar)


if __name__ == "__main__":
    main()
