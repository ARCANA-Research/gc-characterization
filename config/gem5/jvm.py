import argparse
import pathlib
import sys
import time
import yaml

from gem5.coherence_protocol import CoherenceProtocol
from gem5.isas import ISA
from gem5.resources.resource import DiskImageResource, KernelResource
from gem5.simulate.exit_event import ExitEvent
from gem5.simulate.simulator import Simulator
from gem5.utils.requires import requires

requires(
    isa_required=ISA.X86,
    coherence_protocol_required=CoherenceProtocol.MESI_THREE_LEVEL,
)

# ================================= ARGPARSE ================================= #

parser = argparse.ArgumentParser()
parser.add_argument("--ramulator_config", required=True, type=str)
parser.add_argument("--ramulator_output", required=True, type=str)
parser.add_argument("--ramulator_trace", required=True, type=str)
parser.add_argument("--config_path", required=True, type=str)
parser.add_argument("--jdk_cmd", required=True, type=str)
parser.add_argument("--gem5_config_dir", required=True, type=str)
parser.add_argument("--benchmark_image_path", required=True, type=str)
parser.add_argument("--ubuntu_image_path", required=True, type=str)
parser.add_argument("--kernel_path", required=True, type=str)
parser.add_argument("--copy_jfr", required=False, type=str)
args = parser.parse_args()
p_config = args.config_path

sys.path.append(args.gem5_config_dir)
from base import *

# =============================== PARSE CONFIG =============================== #

config = parse_yaml(p_config)

# ================================= SETUP HW ================================= #

switch_cpu = config["hardware"]["cpu"]["cpu_type"]["switch"]
if bool(config["hardware"]["cpu"]["switch_cpu"]) == False:
    switch_cpu = config["hardware"]["cpu"]["cpu_type"]["start"]

processor = setup_processor(
    start_cpu=config["hardware"]["cpu"]["cpu_type"]["start"],
    switch_cpu=switch_cpu,
    num_cores=int(config["hardware"]["cpu"]["cores"]),
)

memory = setup_memory(
    mem_size=config["hardware"]["ramulator2"]["size"],
    create_ramulator2_trace=config["hardware"]["ramulator2"]["create_trace"],
    p_ramulator_config=args.ramulator_config,
    p_ramulator_output=args.ramulator_output,
    p_ramulator_trace=args.ramulator_trace,
)

cache = setup_cache(
    cache_type=config["hardware"]["cache"]["cache_type"],
    switch_cpu=switch_cpu,
    l1d_size=config["hardware"]["cache"]["l1d"]["size"],
    l1d_assoc=config["hardware"]["cache"]["l1d"]["assoc"],
    l1i_size=config["hardware"]["cache"]["l1i"]["size"],
    l1i_assoc=config["hardware"]["cache"]["l1i"]["assoc"],
    l2_size=config["hardware"]["cache"]["l2"]["size"],
    l2_assoc=config["hardware"]["cache"]["l2"]["assoc"],
    l3_size=config["hardware"]["cache"]["l3"]["size"],
    l3_assoc=config["hardware"]["cache"]["l3"]["assoc"],
    l3_banks=config["hardware"]["cpu"]["cores"],
)

# ================================ SETUP BOARD =============================== #

board = setup_board(
    cpu_frequency=config["hardware"]["cpu"]["frequency"],
    memory=memory,
    processor=processor,
    cache=cache,
    benchmark_image_path=args.benchmark_image_path,
)

# ================================= JAVA CMD ================================= #

f_jdk_cmd = open(args.jdk_cmd, "r")
m5_cmd = f"{f_jdk_cmd.readline()}"
f_jdk_cmd.close()

if args.copy_jfr is not None:
    m5_cmd += f";{copy_jfr_command(args.copy_jfr)};"

# ================================= SETUP OS ================================= #

kernel_args = board.get_default_kernel_args()
if bool(config["simulator"]["skip_systemd"]) == True:
    kernel_args.append("no_systemd")
board.set_kernel_disk_workload(
    kernel=KernelResource(
        local_path=args.kernel_path,
        architecture=ISA.X86,
    ),
    disk_image=DiskImageResource(
        local_path=args.ubuntu_image_path,
        root_partition="2",
    ),
    readfile_contents=m5_cmd,
    kernel_args=kernel_args,
)

# =============================== EXIT HANDLER =============================== #

start_time = time.time()


def exit_event_handler():
    print(f"[{time.time() - start_time}s] JDKEXIT: 1 -> Kernel Loaded")
    yield False
    print(f"[{time.time() - start_time}s] JDKEXIT: 2 -> Ubuntu Booted")
    yield False
    print(f"[{time.time() - start_time}s] JDKEXIT: 3 -> Switching CPUs")
    yield False
    print(f"[{time.time() - start_time}s] JDKEXIT: 4 -> Start ROI")
    yield False
    print(f"[{time.time() - start_time}s] JDKEXIT: 5 -> Simulation End")
    yield True


# ================================== START =================================== #

simulator = Simulator(
    board=board,
    on_exit_event={
        ExitEvent.EXIT: exit_event_handler(),
    },
)

simulator._instantiate()
simulator.run()
