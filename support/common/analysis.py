import copy
import numpy
import pandas
import sys

from typing import Any, Dict, List, Set

from common import excel, jvm, op, progress, utils


def split_process_and_sampled_data(l_data: List) -> [List, List]:
    l_sampled = list()
    l_process = list()
    for d_data in l_data:
        # do not sample multiple iterations due to inconsistency
        assert len(d_data["data"]) == 1
        d_iteration = d_data["data"][0]
        if "sampled" not in d_iteration:
            l_process.append(d_data)
        else:
            if d_iteration["sampled"] == True:
                l_sampled.append(d_data)
            else:
                l_process.append(d_data)
    assert len(l_data) == (len(l_sampled) + len(l_process))
    return l_process, l_sampled


def get_combined_and_per_phase_counters(d_results: Dict) -> [List, List, int]:
    # assume all data have same counters, which should be fair due to checker!
    assert len(d_results) > 0
    assert "data" in d_results[0]
    assert len(d_results[0]["data"]) > 0
    assert "data" in d_results[0]["data"][0]
    expected_iterations = len(d_results[0]["data"])
    l_combined_counters = list(d_results[0]["data"][0]["data"].keys())
    l_per_phase_counters = list()
    if "per_phase" in d_results[0]["data"][0]:
        assert "data" in d_results[0]["data"][0]["per_phase"]
        l_per_phase_counters = list(d_results[0]["data"][0]["per_phase"]["data"].keys())
    return l_combined_counters, l_per_phase_counters, expected_iterations


def get_valid_analysis(
    p_analysis: str,
    l_combined_counters: List,
    l_per_phase_counters: List,
    expected_iterations: int,
) -> List:
    s_combined_counters = set(l_combined_counters)
    s_per_phase_counters = set(l_per_phase_counters)
    l_all_analysis = utils.parse_yaml(p_analysis)
    l_valid_analysis = list()
    for d_analysis in l_all_analysis:
        f_func = None
        b_combined = True
        b_per_phase = True
        if d_analysis["type"] == "accuracy":
            f_func = generate_accuracy_data
            for counter in d_analysis["counters"].values():
                if counter not in s_combined_counters:
                    b_combined = False
                if counter not in s_per_phase_counters:
                    b_per_phase = False
            # do not know how to average multiple iterations of per phase data
            if expected_iterations > 1:
                b_per_phase = False
        elif d_analysis["type"] == "count":
            f_func = generate_count_data
            for counter in d_analysis["counters"]:
                if counter not in s_combined_counters:
                    b_combined = False
                if counter not in s_per_phase_counters:
                    b_per_phase = False
            # do not know how to average multiple iterations of per phase data
            if expected_iterations > 1:
                b_per_phase = False
        elif d_analysis["type"] == "overhead":
            f_func = generate_overhead_data
            for counter in d_analysis["counters"]:
                if counter not in s_combined_counters:
                    b_combined = False
                if counter not in s_per_phase_counters:
                    b_per_phase = False
            # do not know how to average multiple iterations of per phase data
            if expected_iterations > 1:
                b_per_phase = False
        elif d_analysis["type"] == "division":
            f_func = generate_division_data
            for counter in d_analysis["counters"].values():
                if counter not in s_combined_counters:
                    b_combined = False
                if counter not in s_per_phase_counters:
                    b_per_phase = False
            # do not know how to average multiple iterations of per phase data
            if expected_iterations > 1:
                b_per_phase = False
        elif d_analysis["type"] == "static":
            f_func = generate_static_data
            if d_analysis["counter"] not in s_combined_counters:
                b_combined = False
            # static counters do not have per phase analysis
            b_per_phase = False
        elif d_analysis["type"] == "p99":
            f_func = generate_p99_data
            b_combined = False
            if d_analysis["counter"] not in s_per_phase_counters:
                b_per_phase = False
        elif d_analysis["type"] == "mean":
            f_func = generate_mean_data
            b_combined = False
            if d_analysis["counter"] not in s_per_phase_counters:
                b_per_phase = False
        elif d_analysis["type"] == "resource_usage":
            f_func = generate_resource_usage_data
            if d_analysis["counter"] not in s_combined_counters:
                b_combined = False
            # resource usage counters do not have per phase analysis
            b_per_phase = False
        elif d_analysis["type"] == "heap_usage":
            f_func = generate_heap_usage_data
            if d_analysis["counter"] not in s_combined_counters:
                b_combined = False
            # reclaim rate counters do not have per phase analysis
            b_per_phase = False
        elif d_analysis["type"] == "gc_frequency":
            f_func = generate_gc_frequency_data
            if d_analysis["counters"]["time"] not in s_combined_counters:
                b_combined = False
            if d_analysis["counters"]["gc_event_count"] not in s_combined_counters:
                b_combined = False
            # gc frequency counters do not have per phase analysis
            b_per_phase = False
        else:
            print(f"Analysis type unimplemented : {expected_analysis['type']}")
            sys.exit(1)
        d_analysis["FUNCTION"] = f_func
        d_analysis["PER_PHASE"] = b_per_phase
        d_analysis["COMBINED"] = b_combined
        if b_combined == True or b_per_phase == True:
            l_valid_analysis.append(d_analysis)
    return l_valid_analysis


def get_event_data(l_data: List, event: str, per_phase: bool) -> List:
    d_event_data = dict()
    # do not know how to average multiple per phase events
    # if per_phase == True:
    #     assert len(l_data) == 1
    for iteration_data in l_data:
        d_data = None
        if per_phase == True:
            d_data = iteration_data["per_phase"]["data"]
        else:
            d_data = iteration_data["data"]
        event_data = d_data[event]
        for phase in event_data.keys():
            if phase not in d_event_data.keys():
                d_event_data[phase] = list()
            d_event_data[phase].append(event_data[phase])
    return d_event_data


def get_event_phases(l_data: List, event: str) -> List:
    l_event_data = list()
    for iteration_data in l_data:
        l_event_data.append(iteration_data["per_phase"]["phases"])
    return l_event_data


def remove_numpy(o_data: Any) -> List:
    if isinstance(o_data, dict):
        for k in o_data.keys():
            o_data[k] = remove_numpy(o_data[k])
        return o_data
    elif isinstance(o_data, list):
        for idx in range(len(o_data)):
            o_data[idx] = remove_numpy(o_data[idx])
        return o_data
    if isinstance(o_data, (numpy.integer, numpy.floating)):
        return float(o_data)
    return o_data


def generate_analysis(
    l_data: List, l_analysis: List, per_phase: bool, prepend_title: str = ""
) -> [List, List]:
    l_per_phase_analysis = list()
    l_combined_analysis = list()
    progress_bar = progress.start(f"Analysing Data", len(l_analysis))
    for d_analysis in l_analysis:
        if (per_phase == True and d_analysis["PER_PHASE"] == False) or (
            per_phase == False and d_analysis["COMBINED"] == False
        ):
            progress.advance(progress_bar)
            continue
        # bool tells if data is per phase or combined
        l_analysis_data, b_per_phase_data = d_analysis["FUNCTION"](
            l_data, d_analysis, per_phase
        )
        l_analysis_data = remove_numpy(l_analysis_data)
        if b_per_phase_data == True:
            l_per_phase_analysis.append(
                {
                    "title": prepend_title + d_analysis["title"],
                    "data": l_analysis_data,
                }
            )
        else:
            l_combined_analysis.append(
                {
                    "title": prepend_title + d_analysis["title"],
                    "data": l_analysis_data,
                }
            )
        progress.advance(progress_bar)
    progress.end(progress_bar)
    return l_combined_analysis, l_per_phase_analysis


def get_empty_data_dict(d_data: Dict, per_phase: bool) -> Dict:
    d_empty = {
        "benchmark": d_data["benchmark"],
        "gc": d_data["gc"],
        "heap": d_data["heap"],
        "heap_multiplier": d_data["heap_multiplier"],
        "iterations": len(d_data["data"]),
    }
    if per_phase == True:
        assert len(d_data["data"]) > 0
        if "per_phase" in d_data["data"][0]:
            d_empty["phases"] = copy.deepcopy(d_data["data"][0]["per_phase"]["phases"])
    return d_empty


def generate_division_data(
    l_data: List, analysis: Dict, per_phase: bool
) -> [List, bool]:
    l_excel = list()
    for data in l_data:
        d_data = get_empty_data_dict(data, per_phase)
        numerator_data = get_event_data(
            data["data"], analysis["counters"]["numerator"], per_phase
        )
        denominator_data = get_event_data(
            data["data"], analysis["counters"]["denominator"], per_phase
        )
        division_data = op.op_binary(numerator_data, denominator_data, op.op_divide)
        if per_phase == False:
            d_data["data"] = op.op_unary(division_data, op.op_mean)
        else:
            d_data["data"] = division_data
        l_excel.append(d_data)
    return l_excel, per_phase


def generate_accuracy_data(
    l_data: List, analysis: Dict, per_phase: bool
) -> [List, bool]:
    l_excel = list()
    for data in l_data:
        d_data = get_empty_data_dict(data, per_phase)
        total_data = None
        hit_data = None
        miss_data = get_event_data(
            data["data"], analysis["counters"]["miss"], per_phase
        )
        if "hit" in analysis["counters"]:
            hit_data = get_event_data(
                data["data"], analysis["counters"]["hit"], per_phase
            )
            total_data = op.op_binary(hit_data, miss_data, op.op_add)
        else:
            total_data = get_event_data(
                data["data"], analysis["counters"]["total"], per_phase
            )
            hit_data = op.op_binary(total_data, miss_data, op.op_sub)
        accuracy_data = op.op_binary(hit_data, total_data, op.op_divide)
        if per_phase == False:
            d_data["data"] = op.op_unary(accuracy_data, op.op_mean)
        else:
            d_data["data"] = accuracy_data
        l_excel.append(d_data)
    return l_excel, per_phase


def generate_count_data(l_data: List, analysis: Dict, per_phase: bool) -> [List, bool]:
    l_excel = list()
    for data in l_data:
        d_data = get_empty_data_dict(data, per_phase)
        summed_data = None
        for counter in analysis["counters"]:
            counter_data = get_event_data(data["data"], counter, per_phase)
            if summed_data is None:
                summed_data = counter_data
            else:
                summed_data = op.op_binary(counter_data, summed_data, op.op_add)
        if "multiplier" in analysis:
            summed_data = op.op_constant(
                summed_data, float(analysis["multiplier"]), op.op_multiply
            )
        if per_phase == False:
            d_data["data"] = op.op_unary(summed_data, op.op_mean)
        else:
            d_data["data"] = summed_data
        l_excel.append(d_data)
    return l_excel, per_phase


def generate_overhead_data(
    l_data: List, analysis: Dict, per_phase: bool
) -> [List, bool]:
    l_excel = list()
    for data in l_data:
        d_data = get_empty_data_dict(data, per_phase)
        summed_data = None
        for counter in analysis["counters"]:
            counter_data = get_event_data(data["data"], counter, per_phase)
            if summed_data is None:
                summed_data = counter_data
            else:
                summed_data = op.op_binary(counter_data, summed_data, op.op_add)
        overhead_data = dict()
        for event in summed_data.keys():
            overhead_data[event] = op.op_binary(
                summed_data[event], summed_data["NONGC"], op.op_divide
            )
        if per_phase == False:
            d_data["data"] = op.op_unary(overhead_data, op.op_mean)
        else:
            d_data["data"] = overhead_data
        l_excel.append(d_data)
    return l_excel, per_phase


def generate_static_data(l_data: List, analysis: Dict, per_phase: bool) -> [List, bool]:
    l_excel = list()
    for data in l_data:
        d_data = get_empty_data_dict(data, False)
        static_data = get_event_data(data["data"], analysis["counter"], False)
        d_data["data"] = op.op_unary(static_data, op.op_mean)
        l_excel.append(d_data)
    return l_excel, False


def generate_p99_data(l_data: List, analysis: Dict, per_phase: bool) -> [List, bool]:
    # per phase is ignored as a parameter for it, as it requires per phase
    l_excel = list()
    for data in l_data:
        d_data = get_empty_data_dict(data, False)
        p99_data = get_event_data(data["data"], analysis["counter"], True)
        l_phases = get_event_phases(data["data"], analysis["counter"])
        p99_data = remove_non_phase_data(p99_data, l_phases)
        p99_data["GCSTW"] = op.op_unary(
            p99_data["GCSTW"], op.op_merge_continuous_values
        )
        p99_data = op.op_unary(p99_data, op.op_remove_none)
        d_data["data"] = op.op_unary(op.op_unary(p99_data, op.op_x_p99), op.op_mean)
        d_data["data"]["TOTAL"] = None
        d_data["data"]["TOTALGC"] = None
        l_excel.append(d_data)
    return l_excel, False


def generate_mean_data(l_data: List, analysis: Dict, per_phase: bool) -> [List, bool]:
    # per phase is ignored as a parameter for it, as it requires per phase
    l_excel = list()
    for data in l_data:
        d_data = get_empty_data_dict(data, False)
        mean_data = get_event_data(data["data"], analysis["counter"], True)
        l_phases = get_event_phases(data["data"], analysis["counter"])
        mean_data = remove_non_phase_data(mean_data, l_phases)
        mean_data["GCSTW"] = op.op_unary(
            mean_data["GCSTW"], op.op_merge_continuous_values
        )
        mean_data = op.op_unary(mean_data, op.op_remove_none)
        d_data["data"] = op.op_unary(op.op_unary(mean_data, op.op_x_mean), op.op_mean)
        d_data["data"]["TOTAL"] = None
        d_data["data"]["TOTALGC"] = None
        l_excel.append(d_data)
    return l_excel, False


def generate_resource_usage_data(
    l_data: List, analysis: Dict, per_phase: bool
) -> [List, bool]:
    l_excel = list()
    for data in l_data:
        d_data = get_empty_data_dict(data, False)
        usage_data = get_event_data(data["data"], analysis["counter"], False)
        # gc cpu percent requires mean over indices representing cpus
        d_data["data"] = op.op_unary(usage_data, op.op_y_mean)
        l_excel.append(d_data)
    return l_excel, False


def generate_heap_usage_data(
    l_data: List, analysis: Dict, per_phase: bool
) -> [List, bool]:
    l_excel = list()
    for data in l_data:
        d_data = get_empty_data_dict(data, False)
        heap_usage = get_event_data(data["data"], analysis["counter"], False)
        # gc reclaim rate requires mean over indices representing cpus
        # genz has negative rate...
        d_data["data"] = op.op_unary(heap_usage, op.op_x_average)
        d_data["data"] = op.op_unary(d_data["data"], op.op_average)
        l_excel.append(d_data)
    return l_excel, False


def generate_gc_frequency_data(
    l_data: List, analysis: Dict, per_phase: bool
) -> [List, bool]:
    l_excel = list()
    for data in l_data:
        d_data = get_empty_data_dict(data, per_phase)
        time_data = get_event_data(data["data"], analysis["counters"]["time"], False)
        gc_event_count_data = get_event_data(
            data["data"], analysis["counters"]["gc_event_count"], False
        )
        time_data["GCSTW"] = time_data["TOTAL"]
        for k in gc_event_count_data.keys():
            if k != "GCSTW":
                gc_event_count_data[k] = [0] * len(gc_event_count_data[k])
        frequency_data = op.op_binary(time_data, gc_event_count_data, op.op_divide)
        d_data["data"] = op.op_unary(frequency_data, op.op_mean)
        l_excel.append(d_data)
    return l_excel, False


def remove_non_phase_data(d_data_original: Dict, l_phases: Dict) -> Dict:
    d_data = copy.deepcopy(d_data_original)
    for iteration in range(len(l_phases)):
        for phase in d_data.keys():
            if phase == "NONGC":
                for idx in range(len(d_data[phase][iteration])):
                    if l_phases[iteration][idx] != 1:
                        d_data[phase][iteration][idx] = None
            elif phase == "CONCURRENTGC":
                for idx in range(len(d_data[phase][iteration])):
                    if l_phases[iteration][idx] != 1:
                        d_data[phase][iteration][idx] = None
            elif phase == "GCSTW":
                for idx in range(len(d_data[phase][iteration])):
                    if l_phases[iteration][idx] < 2:
                        d_data[phase][iteration][idx] = None
            else:
                d_data[phase][iteration] = list()
    return d_data
