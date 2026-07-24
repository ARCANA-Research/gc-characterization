import argparse
import copy
import glob
import os
import shutil
import sys
import yaml

from typing import List

sys.path.append(os.path.abspath("support"))
from common import jvm, utils
from typing import List, Dict


def copy_counters_file(config: "yaml.YAMLObject", p_counter_out: str) -> str:
    f_counters = open(f"{p_counter_out}.yaml", "w")
    p_counter = os.path.abspath(f"counters/{config['counter']['counter']}")
    with utils.CommonFile(p_counter, "r") as f_counter_base:
        try:
            counter = yaml.safe_load(f_counter_base)
            yaml.dump(counter, f_counters)
            f_counters.close()
            return p_counter
        except yaml.YAMLError as err:
            print(err)


def setup_tokens(
    config: "yaml.YAMLObject",
    p_counterdir: str,
    p_output: str,
    p_build: str,
    p_tmp: str,
) -> Dict:
    return {
        "COUNTERDIR": p_counterdir,
        "COUNTEROUTDIR": p_output,
        "COUNTERBUILDDIR": p_build,
        "COUNTERBENCHMARKS": config["benchmark"],
        "COUNTERJVMCORECOUNT": config["jdk"]["num-cpus"],
        "COUNTERGCAFFINITYMASK": utils.generate_bit_mask(
            config["counter"]["gc-cpus"], config["counter"]["num-cpus"]
        ),
        "COUNTERJVMAFFINITYMASK": utils.generate_bit_mask(
            config["counter"]["jvm-cpus"], config["counter"]["num-cpus"]
        ),
        "COUNTERJVMCPULIST": ",".join(
            str(cpuid) for cpuid in config["counter"]["jvm-cpus"]
        ),
        "COUNTERNUMANODE": config["counter"]["numa-node"],
        "COUNTERJDKPATH": jvm.get_jvm_path(config),
        "COUNTERRUNS": config[config["suite"]]["runs"],
        "COUNTERTIMEOUT": config[config["suite"]]["timeout"],
        "COUNTERDACAPOPATH": config["dacapo"]["path"],
        "JDKVERSION": config["jdk"]["version"],
        "COUNTERITERATIONS": config["counter"]["iterations"],
        "COUNTERMAXATTEMPTS": config["counter"]["max-attempts"],
        "COUNTERMINHEAPMULTIPLIER": config["jdk"]["heap-multiplier"],
        "COUNTERTMPDIR": p_tmp,
        "CURRDIR": p_counterdir,
        "COUNTERAGENTLIBRARY": config["counter"]["agent"],
        "COUNTERSIZE": config["size"],
    }


def main():
    config = utils.parse_yaml("config.yaml")
    p_support = os.path.abspath("support")
    p_counterdir = utils.get_currdir()
    p_build = f"{p_counterdir}/build/src/counter"
    p_output, p_tmp = utils.create_output_folder(
        config["out"]["path"], os.path.abspath("tmp"), config["benchmark"]
    )
    p_counter = f"{p_output}/counters.yaml"
    os.makedirs(f"{p_output}/running")
    p_running_configs = f"{p_output}/running/configs"
    os.makedirs(p_running_configs)
    y_counters = utils.parse_yaml(
        f"{p_counterdir}/counters/{config['counter']['counter']}"
    )
    y_counters["gc-cpus"] = config["counter"]["gc-cpus"]
    y_counters["jvm-cpus"] = config["counter"]["jvm-cpus"]
    utils.save_yaml(y_counters, p_counter)
    shutil.copyfile(f"support/eventmap.yaml", f"{p_output}/eventmap.yaml")
    shutil.copytree(f"{p_support}/jfr", f"{p_output}/jfr")
    base_config = utils.parse_yaml(
        f"{p_counterdir}/running/counter/{config['running-ng']['config'][config['suite']]}"
    )
    base_tokens = setup_tokens(config, p_counterdir, p_output, p_build, p_tmp)
    updated_config = copy.deepcopy(config)
    updated_config["running-ng"] = utils.dict_replace_tokens(
        updated_config["running-ng"], base_tokens
    )
    utils.save_yaml(updated_config, f"{p_output}/config.yaml")
    for gc in config["gc"]:
        tokens = copy.deepcopy(base_tokens)
        tokens["COUNTERGC"] = gc
        tokens["COUNTERMINHEAP"] = jvm.get_gc_minheap(p_support, gc, config)
        gc_config = utils.dict_replace_tokens(copy.deepcopy(base_config), tokens)
        utils.save_yaml(gc_config, f"{p_running_configs}/{gc}.yaml")
    utils.move_config_includes(p_running_configs, base_tokens)
    print(p_output)


if __name__ == "__main__":
    main()
