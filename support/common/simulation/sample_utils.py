import os

from common import utils
from common.simulation import check_utils, gem5, ramulator2

from typing import Callable, List

STAT_COUNTERS = {
    "GEM5_STATS_FILE_VALID",
    "GEM5_STATS_PHASES_MATCH_SIMULATION",
    "GEM5_STATS_VALID_EVENTS",
    "RAMUALTOR2_STATS_FILE_VALID",
    "RAMUALTOR2_TRACE_FILE_VALID",
    "RAMULATOR2_STATS_PHASES_MATCH_SIMULATION",
}

MINIMUM_PHASES = 5


def get_sample_path(p_path: str, create_dir: bool = False) -> str:
    p_dir = os.path.dirname(p_path)
    file_name = os.path.basename(p_path)
    file_name_split = os.path.splitext(file_name)
    sample_file_name = file_name_split[0] + "_sample" + "".join(file_name_split[1:])
    p_execution_output = f"{p_dir}/simulation"
    if create_dir == True:
        utils.create_folder_if_not_exist(p_execution_output)
    return f"{p_execution_output}/{sample_file_name}"


def generate_sample_statistics(p_execution: str) -> bool:
    p_simerr = f"{p_execution}/simerr.log"
    p_gem5 = f"{p_execution}/stats.gz"
    p_ramulator2 = f"{p_execution}/ramulator_stats.gz"
    try:
        same_phases = find_number_valid_events(p_ramulator2, p_gem5, p_simerr)
        if same_phases < MINIMUM_PHASES:
            return False
        copy_simerr(p_simerr, get_sample_path(p_simerr), same_phases)
        l_jdk_events = gem5.parse_simerr(get_sample_path(p_simerr))
        assert len(l_jdk_events) == same_phases
        # extra dump at end
        copy_statistics(p_gem5, get_sample_path(p_gem5), gem5, same_phases + 1)
        # extra dump at start
        copy_statistics(
            p_ramulator2, get_sample_path(p_ramulator2), ramulator2, same_phases + 1
        )
    except Exception as e:
        print(f"SAMPLEERROR: {str(e)}")
        return False
    return True


def find_number_valid_events(p_ramulator2: str, p_gem5: str, p_simerr: str) -> int:
    l_jdk_events = gem5.parse_simerr(p_simerr)
    l_gem5_events = parse_statistics_events(
        p_gem5, "statJdkPhase", len(l_jdk_events) + 1, gem5
    )
    l_ramulator2_events = parse_statistics_events(
        p_ramulator2, "jdk_execution_phase:", len(l_jdk_events) + 1, ramulator2
    )
    same_phases = 0
    l_gem5_events = l_gem5_events[:-1]
    l_ramulator2_events = l_ramulator2_events[1:]
    if len(l_jdk_events) != len(l_gem5_events):
        return same_phases
    if len(l_jdk_events) != len(l_ramulator2_events):
        return same_phases
    for idx in range(len(l_jdk_events)):
        if (
            l_jdk_events[idx] == l_gem5_events[idx]
            and l_jdk_events[idx] == l_ramulator2_events[idx]
        ):
            same_phases += 1
        else:
            break
    # ensure that we do not end execution on a gc phase, but rather application phase
    while same_phases != 0 and l_jdk_events[same_phases - 1] != 1:
        same_phases -= 1
    return same_phases


def parse_statistics_events(
    p_src: str, s_token: str, phase_size: int, instrument_module: Callable
) -> List:
    l_phases = [0] * phase_size
    with utils.CommonFile(p_src, "r") as f_src:
        current_phase = None
        phases_added = 0
        in_statistic = False
        try:
            for line_src in f_src:
                if in_statistic == True:
                    if instrument_module.END_STATISTIC_TOKEN in line_src:
                        if current_phase is None:
                            raise Exception(f"Phase not found -> {p_src}")
                        l_phases[phases_added] = current_phase
                        current_phase = None
                        phases_added += 1
                        in_statistic = False
                    elif instrument_module.START_STATISTIC_TOKEN in line_src:
                        raise Exception("Start token not closed")
                    else:
                        if s_token in line_src:
                            current_phase = int(line_src.split()[-1])
                else:
                    if instrument_module.START_STATISTIC_TOKEN in line_src:
                        in_statistic = True
        except EOFError as eof_e:
            return l_phases
    return l_phases


def copy_simerr(p_src: str, p_dst: str, events_to_copy: int) -> str:
    print(f"SAMPLE: Generating -> {p_dst} from {p_src}")
    events_copied = 0
    with utils.CommonFile(p_dst, "w") as f_dst:
        with utils.CommonFile(p_src, "r") as f_src:
            try:
                for line_src in f_src:
                    if "DUMP AND RESET STATS FOR PHASE" in line_src:
                        events_copied += 1
                    f_dst.write(line_src)
                    if events_copied == events_to_copy:
                        return
            except EOFError as eof_e:
                return p_dst
            except Exception as e:
                raise Exception(e)


def copy_statistics(
    p_src: str, p_dst: str, instrument_module: Callable, phases_to_copy: int
) -> str:
    print(f"SAMPLE: Generating -> {p_dst} from {p_src}")
    with utils.CommonFile(p_dst, "w") as f_dst:
        l_current_dump = list()
        in_statistic = False
        events_copied = 0
        with utils.CommonFile(p_src, "r") as f_src:
            try:
                for line_src in f_src:
                    if in_statistic == True:
                        if instrument_module.END_STATISTIC_TOKEN in line_src:
                            l_current_dump.append(line_src)
                            for line_dst in l_current_dump:
                                f_dst.write(line_dst)
                            events_copied += 1
                            if events_copied == phases_to_copy:
                                return
                            l_current_dump.clear()
                            in_statistic = False
                        elif instrument_module.START_STATISTIC_TOKEN in line_src:
                            raise Exception("Start token not closed")
                        else:
                            l_current_dump.append(line_src)
                    else:
                        if instrument_module.START_STATISTIC_TOKEN in line_src:
                            l_current_dump.append(line_src)
                            in_statistic = True
            except EOFError as eof_e:
                return
            except Exception as e:
                raise Exception(e)
