import m5
import pathlib
import sys
import yaml

from gem5.isas import ISA
from gem5.resources.resource import DiskImageResource
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.boards.jdk_board import JdkBoard
from gem5.components.cachehierarchies.classic.no_cache import NoCache
from gem5.components.cachehierarchies.classic.private_l1_private_l2_shared_l3_cache_hierarchy import (
    PrivateL1PrivateL2SharedL3CacheHierarchy,
)
from gem5.components.cachehierarchies.ruby.mesi_three_level_cache_hierarchy import (
    MESIThreeLevelCacheHierarchy,
)
from gem5.components.memory.ramulator2_memory import Ramulator2Memory
from gem5.components.memory.single_channel import SingleChannelDDR3_1600
from gem5.components.processors.simple_switchable_processor import (
    SimpleSwitchableProcessor,
)


def parse_yaml(p_yaml: str) -> "yaml.YAMLObject":
    with open(p_yaml) as f_yaml:
        try:
            yaml_obj = yaml.safe_load(f_yaml)
            return yaml_obj
        except yaml.YAMLError as err:
            print(err)


def select_cpu(cpu: str) -> "CPUTypes":
    if cpu == "o3":
        return CPUTypes.O3
    elif cpu == "atomic":
        return CPUTypes.ATOMIC
    elif cpu == "kvm":
        return CPUTypes.KVM
    elif cpu == "timing":
        raise Exception(
            "JDKERROR: Timing CPU's Ruby model does not support GC isolation"
        )
    raise Exception(f'JDKERROR: Unknown CPU type"{cpu}"')


def setup_processor(start_cpu: str, switch_cpu: str, num_cores: int) -> "Processor":
    processor = SimpleSwitchableProcessor(
        starting_core_type=select_cpu(start_cpu),
        switch_core_type=select_cpu(switch_cpu),
        isa=ISA.X86,
        num_cores=num_cores,
    )
    if select_cpu(start_cpu) == CPUTypes.KVM:
        m5.util.inform("KVM: Disabling Performance Counters")
        for proc in processor.start:
            proc.core.usePerf = False
    return processor


def setup_cache(
    cache_type: str,
    switch_cpu: str,
    l1d_size: int,
    l1d_assoc: int,
    l1i_size: int,
    l1i_assoc: int,
    l2_size: int,
    l2_assoc: int,
    l3_size: int,
    l3_assoc: int,
    l3_banks: int,
) -> "Cache":
    if (
        cache_type == "nocache"
        or select_cpu(switch_cpu) == CPUTypes.ATOMIC
        or select_cpu(switch_cpu) == CPUTypes.KVM
    ):
        m5.util.inform("CACHE: No Cache")
        return NoCache()
    if cache_type == "ruby":
        m5.util.inform("CACHE: MESI Three Level Cache")
        return MESIThreeLevelCacheHierarchy(
            l1d_size=l1d_size,
            l1d_assoc=l1d_assoc,
            l1i_size=l1i_size,
            l1i_assoc=l1i_assoc,
            l2_size=l2_size,
            l2_assoc=l2_assoc,
            l3_size=l3_size,
            l3_assoc=l3_assoc,
            num_l3_banks=l3_banks,
        )
    if cache_type == "simple":
        m5.util.inform("CACHE: Simple Three Level Cache")
        return PrivateL1PrivateL2SharedL3CacheHierarchy(
            l1d_size=l1d_size,
            l1d_assoc=l1d_assoc,
            l1i_size=l1i_size,
            l1i_assoc=l1i_assoc,
            l2_size=l2_size,
            l2_assoc=l2_assoc,
            l3_size=l3_size,
            l3_assoc=l3_assoc,
        )
    m5.util.inform(f"CACHE: Unknown type {cache_type}")
    sys.exit(1)


def setup_memory(
    mem_size: str,
    create_ramulator2_trace: bool,
    p_ramulator_config: str,
    p_ramulator_output: str,
    p_ramulator_trace: str,
) -> "Memory":
    m5.util.inform("MEMORY: Ramulator2")
    return Ramulator2Memory(
        config_path=p_ramulator_config,
        output_path=p_ramulator_output,
        size=mem_size,
        trace_path=p_ramulator_trace,
        create_trace=create_ramulator2_trace,
    )


def setup_board(
    cpu_frequency: str,
    memory: "Memory",
    processor: "Processor",
    cache: "Cache",
    benchmark_image_path: str,
) -> "Board":
    return JdkBoard(
        clk_freq=cpu_frequency,
        processor=processor,
        memory=memory,
        cache_hierarchy=cache,
        benchmark_image=DiskImageResource(local_path=benchmark_image_path),
        mount_benchmark_as_cow=True,
    )


def copy_jfr_command(src_file: str) -> str:
    dst_path = f"{m5.options.outdir}/{pathlib.Path(src_file).name}"
    m5.util.inform(f"COPYFILE: Generated command for {src_file} -> {dst_path}")
    return f"gem5-bridge writefile {src_file} {dst_path}"
