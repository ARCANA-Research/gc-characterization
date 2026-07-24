import copy
import os
import pandas

from collections import OrderedDict
from typing import Callable, Dict, List

from common import jvm, op, progress, utils


def add_line_column(l_table: List, line_value: int) -> List:
    for idx in range(len(l_table)):
        l_table[idx]["Line"] = line_value
    return l_table


def remove_benchmark_name(l_table: List) -> List:
    for idx in range(len(l_table)):
        if "GC" in l_table[idx] and l_table[idx]["GC"] != "Z":
            l_table[idx]["Benchmark"] = ""
    return l_table


def shorten_sheet_name(sheet_name: str, unique_append: int) -> str:
    if len(sheet_name) > 31:
        old_sheet_name = sheet_name
        unique_append = str(unique_append).strip()
        short_sheet_name = sheet_name[: 31 - len(unique_append)]
        short_sheet_name += unique_append
        assert len(short_sheet_name) == 31
        sheet_name = short_sheet_name
        print(f"Title too long -> {old_sheet_name} and changed to -> {sheet_name}")
    return sheet_name


def generate_excel(
    d_analysis: Dict,
    sheet_name: str,
    d_data: Dict,
    p_eventmap: str,
    plot_function: Callable,
    curr_sheet_count: int,
    suite_name: str,
) -> ["DataFrame", str]:
    if plot_function.__name__ == "heatmap" and d_analysis["title"] != "gc-cpu-percent":
        return None, None
    if plot_function.__name__ != "heatmap" and d_analysis["title"] == "gc-cpu-percent":
        return None, None
    df = plot_function(p_eventmap, d_data, suite_name)
    sheet_name = shorten_sheet_name(sheet_name, curr_sheet_count)
    return df, sheet_name


def save_excel(
    l_analysis: List,
    p_excel: str,
    p_eventmap: str,
    plot_function: Callable,
    suite_name: str,
    file_name_append: str = None,
) -> None:
    if len(l_analysis) == 0:
        return
    s_file_name = plot_function.__name__
    if file_name_append is not None:
        s_file_name += f"-{file_name_append}"
    xl_writer = None
    curr_sheet_count = 0
    progress_bar = progress.start(f"Generating {s_file_name}", len(l_analysis))
    for d_analysis in l_analysis:
        curr_sheet_count += 1
        df, sheet_name = generate_excel(
            d_analysis,
            d_analysis["title"],
            d_analysis["data"],
            p_eventmap,
            plot_function,
            curr_sheet_count,
            suite_name,
        )
        if df is not None:
            if xl_writer is None:
                xl_writer = pandas.ExcelWriter(f"{p_excel}/{s_file_name}.xlsx")
            df.to_excel(xl_writer, sheet_name=sheet_name, index=True)
        progress.advance(progress_bar)
    progress.end(progress_bar)
    if xl_writer is not None:
        xl_writer.close()


def save_excel_per_analysis(
    l_analysis: List, p_excel: str, p_eventmap: str, file_name_append: str = None
) -> None:
    if len(l_analysis) == 0:
        return
    p_dir = f"{p_excel}/per_phase"
    if file_name_append is not None:
        p_dir += f"-{file_name_append}"
    utils.create_folder_if_not_exist_and_archive_existing_files(p_dir)
    progress_bar = progress.start(f"Generating Per Phase Excel", len(l_analysis))
    for d_analysis in l_analysis:
        curr_sheet_count = 0
        xl_writer = None
        for d_data in d_analysis["data"]:
            bm_sheet_name = f"{d_data['benchmark']}_{d_data['gc']}"
            curr_sheet_count += 1
            df, sheet_name = generate_excel(
                d_analysis,
                bm_sheet_name,
                d_data,
                p_eventmap,
                per_phase,
                curr_sheet_count,
            )
            if xl_writer is None:
                xl_writer = pandas.ExcelWriter(f"{p_dir}/{d_analysis['title']}.xlsx")
            df.to_excel(xl_writer, sheet_name=sheet_name, index=True)
        if xl_writer is not None:
            xl_writer.close()
        progress.advance(progress_bar)
    progress.end(progress_bar)


# ============================ PER BENCHMARK SHEET =========================== #


def create_empty_per_benchmark_table(suite_name: str) -> List:
    l_table = list()
    l_table.append({"Benchmark": ""})
    for benchmark in jvm.BENCHMARK_LIST[suite_name]:
        for gc in jvm.GC_LIST:
            d_execution = {
                "Benchmark": benchmark,
                "GC": gc,
                "Heap": None,
                "Heap Multiplier": None,
                "Iterations": None,
            }
            d_execution.update(jvm.get_base_phase_dict(None))
            for phase_id in range(jvm.NUM_GC_PHASES):
                d_execution[phase_id] = None
            l_table.append(d_execution)
        l_table.append({"Benchmark": ""})
        l_table.append({"Benchmark": ""})
        l_table.append({"Benchmark": ""})
    return l_table


def per_benchmark(p_eventmap: str, l_data: List, suite_name: str) -> "DataFrame":
    l_table = create_empty_per_benchmark_table(suite_name)
    d_gc_phases = jvm.valid_custom_phases(p_eventmap)
    for d_data in l_data:
        for table_row in l_table:
            if (
                table_row["Benchmark"] == d_data["benchmark"]
                and table_row["GC"] == d_data["gc"]
            ):
                # Make sure existing data is not overwritten
                assert table_row["Heap"] is None
                table_row["Benchmark"] = d_data["benchmark"]
                table_row["GC"] = d_data["gc"]
                table_row["Heap"] = d_data["heap"]
                table_row["Heap Multiplier"] = d_data["heap_multiplier"]
                table_row["Iterations"] = d_data["iterations"]
                gc = d_data["gc"]
                for gc_phase in d_data["data"].keys():
                    if gc_phase in d_gc_phases[gc]:
                        table_row[d_gc_phases[gc][gc_phase]] = d_data["data"][gc_phase]
                    else:
                        table_row[gc_phase] = d_data["data"][gc_phase]
    l_table = add_line_column(l_table, 1)
    l_table = remove_benchmark_name(l_table)
    return pandas.DataFrame(l_table)


# =============================== PER GC SHEET =============================== #


def create_empty_per_gc_table(suite_name: str) -> List:
    l_table = list()
    for gc in jvm.GC_LIST:
        for benchmark in jvm.BENCHMARK_LIST[suite_name]:
            d_execution = {
                "Benchmark": benchmark,
                "GC": gc,
                "Heap": None,
                "Heap Multiplier": None,
                "Iterations": None,
            }
            d_execution.update(jvm.get_base_phase_dict(None))
            for phase_id in range(jvm.NUM_GC_PHASES):
                d_execution[phase_id] = None
            l_table.append(d_execution)
        l_table.append({"Benchmark": ""})
    return l_table


def per_gc(p_eventmap: str, l_data: List, suite_name: str) -> "DataFrame":
    l_table = create_empty_per_gc_table(suite_name)
    d_gc_phases = jvm.valid_custom_phases(p_eventmap)
    for d_data in l_data:
        for table_row in l_table:
            if (
                table_row["Benchmark"] == d_data["benchmark"]
                and table_row["GC"] == d_data["gc"]
            ):
                # Make sure existing data is not overwritten
                assert table_row["Heap"] is None
                table_row["Benchmark"] = d_data["benchmark"]
                table_row["GC"] = d_data["gc"]
                table_row["Heap"] = d_data["heap"]
                table_row["Heap Multiplier"] = d_data["heap_multiplier"]
                table_row["Iterations"] = d_data["iterations"]
                gc = d_data["gc"]
                for gc_phase in d_data["data"].keys():
                    if gc_phase in d_gc_phases[gc]:
                        table_row[d_gc_phases[gc][gc_phase]] = d_data["data"][gc_phase]
                    else:
                        table_row[gc_phase] = d_data["data"][gc_phase]
    l_table = add_line_column(l_table, 1)
    return pandas.DataFrame(l_table)


# ================================ BY GC SHEET =============================== #


def create_empty_by_gc_table(suite_name: str) -> List:
    l_table = list()
    for benchmark in jvm.BENCHMARK_LIST[suite_name]:
        d_execution = {
            ("Benchmark", "Benchmark"): benchmark,
        }
        for phase in jvm.BASE_PHASES:
            for gc in jvm.GC_LIST:
                d_execution[(phase, gc)] = None
        l_table.append(d_execution)
    return l_table


def by_gc(p_eventmap: str, l_data: List, suite_name: str) -> "DataFrame":
    l_table = create_empty_by_gc_table(suite_name)
    for d_data in l_data:
        for table_row in l_table:
            if table_row[("Benchmark", "Benchmark")] == d_data["benchmark"]:
                for phase in jvm.BASE_PHASES:
                    if phase not in d_data["data"]:
                        continue
                    col_tuple = (phase, d_data["gc"])
                    assert table_row[col_tuple] is None
                    table_row[col_tuple] = d_data["data"][phase]
    l_table = utils.convert_list_of_dict_to_dict_of_lists(l_table)
    return pandas.DataFrame(l_table)


# ================================ SCALE SHEET =============================== #


def create_empty_scale_table(l_xaxis: List, suite_name: str) -> List:
    l_table = list()
    l_xaxis.sort()
    for benchmark in jvm.BENCHMARK_LIST[suite_name]:
        d_row = {("Benchmark", "Benchmark"): benchmark}
        for gc in jvm.GC_LIST:
            for x_axis in l_xaxis:
                d_row[(gc, x_axis)] = None
        l_table.append(d_row)
    return l_table


def scale(p_eventmap: str, d_data: Dict, suite_name: str) -> "DataFrame":
    l_table = create_empty_scale_table(list(d_data.keys()), suite_name)
    for x_axis in d_data.keys():
        for table_row in l_table:
            bm_name = table_row[("Benchmark", "Benchmark")]
            for bm_gc in jvm.GC_LIST:
                data_hash = f"{bm_name}_{bm_gc}"
                if data_hash in d_data[x_axis]:
                    table_row[(bm_gc, x_axis)] = d_data[x_axis][data_hash]
    l_table = utils.convert_list_of_dict_to_dict_of_lists(l_table)
    return pandas.DataFrame(l_table)


# ============================== BMCOMPARE SHEET ============================= #


def create_empty_bmcompare_table(l_compare: List, bm_name: str) -> List:
    l_table = list()
    for gc in jvm.GC_LIST:
        l_table.append({"Benchmark": ""})
        for compare_k in l_compare:
            l_table.append(
                {"Benchmark": bm_name, "GC": gc, "Name": compare_k, "Value": None}
            )
    return l_table


def get_bmcompare_data(d_data: Dict, bm_name: str, bm_gc: str) -> float:
    if bm_name != "all":
        execution_k = f"{bm_name}_{bm_gc}"
        return d_data[execution_k]
    l_data = list()
    for execution_k in d_data.keys():
        curr_gc = execution_k.split("_")[1]
        if curr_gc == bm_gc:
            if d_data[execution_k] is None:
                return None
            l_data.append(d_data[execution_k])
    # assert len(l_data) == len(jvm.BENCHMARK_LIST["dacapo"])
    if len(l_data) == 0:
        return None
    return op.op_mean(l_data)


def bmcompare(p_eventmap: str, d_data: Dict, suite_name: str) -> "DataFrame":
    assert len(d_data.keys()) > 0
    s_bm_name = set()
    for execution_k in d_data[list(d_data.keys())[0]].keys():
        bm_name = execution_k.split("_")[0]
        s_bm_name.add(bm_name)
    bm_name = "all"
    if len(s_bm_name) == 1:
        bm_name = list(s_bm_name)[0]
    l_table = create_empty_bmcompare_table(list(d_data.keys()), bm_name)
    for group_k in d_data.keys():
        for table_row in l_table:
            bm_name = table_row["Benchmark"]
            if bm_name == "":
                continue
            if table_row["Name"] != group_k:
                continue
            bm_gc = table_row["GC"]
            table_row["Value"] = get_bmcompare_data(d_data[group_k], bm_name, bm_gc)
    return pandas.DataFrame(l_table)


# =============================== HEATMAP SHEET ============================== #


def create_empty_heatmap_table(num_cpus: int) -> List:
    l_table = list()
    for gc in reversed(jvm.GC_LIST):
        d_row = {"GC": gc}
        for core in range(num_cpus):
            d_row[f"Core {core + 1}"] = None
        l_table.append(d_row)
    return l_table


def merge_heatmap_data(l_data: List) -> Dict:
    num_cpus = None
    for data in l_data:
        if num_cpus is None:
            num_cpus = len(data["data"]["TOTAL"])
        if num_cpus < len(data["data"]["TOTAL"]):
            num_cpus = len(data["data"]["TOTAL"])
    d_data = dict()
    d_count = dict()
    if num_cpus is None:
        return dict(), 0
    for gc in jvm.GC_LIST:
        d_data[gc] = [None] * num_cpus
        d_count[gc] = 0
    for data in l_data:
        bm_gc = data["gc"]
        for idx in range(num_cpus):
            if (
                idx < len(data["data"]["TOTAL"])
                and data["data"]["TOTAL"][idx] is not None
            ):
                if d_data[bm_gc][idx] is None:
                    d_data[bm_gc][idx] = 0.0
                d_data[bm_gc][idx] += data["data"]["TOTAL"][idx]
        d_count[bm_gc] += 1
    for gc in jvm.GC_LIST:
        for idx in range(num_cpus):
            if d_data[gc][idx] is not None and d_count[gc] is not None:
                d_data[gc][idx] = op.op_divide(d_data[gc][idx], d_count[gc])
    return d_data, num_cpus


def heatmap(p_eventmap: str, l_data: List, suite_name: str) -> "DataFrame":
    d_data, num_cpus = merge_heatmap_data(l_data)
    l_table = create_empty_heatmap_table(num_cpus)
    for table_row in l_table:
        for core in range(num_cpus):
            table_row[f"Core {core + 1}"] = d_data[table_row["GC"]][core]
    return pandas.DataFrame(l_table)


# ============================== PER PHASE SHEET ============================= #


def create_empty_per_phase_table(d_data: Dict, p_eventmap: str) -> List:
    _, gc_id_to_event_map, _ = jvm.valid_phases(p_eventmap, d_data["gc"], False, True)
    l_table = list()
    for gc_event in d_data["phases"]:
        d_row = {
            "Benchmark": d_data["benchmark"],
            "GC": d_data["gc"],
            "Heap": d_data["heap"],
            "Heap Multiplier": d_data["heap_multiplier"],
            "Iterations": d_data["iterations"],
            "Highlight": 0 if gc_event >= 2 else 1,
            "Event": gc_id_to_event_map[gc_event],
        }
        for base_phase in jvm.BASE_PHASES:
            d_row[base_phase] = None
            d_row[f"{base_phase}_SUMMED"] = None
            d_row[f"{base_phase}_PERCENT"] = None
        l_table.append(d_row)
    return l_table


def per_phase(p_eventmap: str, d_data: Dict, suite_name: str) -> "DataFrame":
    l_table = create_empty_per_phase_table(d_data, p_eventmap)
    for phase in jvm.BASE_PHASES:
        assert len(d_data["data"][phase]) == 1
        l_phase_data = d_data["data"][phase][0]
        phase_total = sum(l_phase_data)
        phase_curr_total = 0
        for idx in range(len(d_data["phases"])):
            l_table[idx][phase] = l_phase_data[idx]
            phase_curr_total += l_phase_data[idx]
            l_table[idx][f"{phase}_SUMMED"] = phase_curr_total
            l_table[idx][f"{phase}_PERCENT"] = op.op_divide(
                phase_curr_total, phase_total
            )
    return pandas.DataFrame(l_table)


# ============================= SPLIT SCALE SHEET ============================ #


def create_empty_split_scale_table(l_label: List) -> List:
    l_table = list()
    l_label = list(l_label)
    l_label.sort()
    for gc in jvm.GC_LIST:
        for label in l_label:
            d_execution = {
                "Label": label,
                "GC": gc,
            }
            d_execution.update(jvm.get_base_phase_dict(None))
            for phase_id in range(jvm.NUM_GC_PHASES):
                d_execution[phase_id] = None
            l_table.append(d_execution)
        l_table.append({"Label": ""})
    return l_table


def split_scale(p_eventmap: str, d_data: Dict, suite_name: str) -> "DataFrame":
    l_table = create_empty_split_scale_table(d_data.keys())
    d_gc_phases = jvm.valid_custom_phases(p_eventmap)
    for label in d_data.keys():
        for table_row in l_table:
            if table_row["Label"] == label:
                # Make sure existing data is not overwritten
                assert table_row["NONGC"] is None
                table_row["Label"] = label
                bm_gc = table_row["GC"]
                for gc_phase in d_data[label][bm_gc].keys():
                    if gc_phase in d_gc_phases[bm_gc]:
                        table_row[d_gc_phases[bm_gc][gc_phase]] = d_data[label][bm_gc][
                            gc_phase
                        ]
                    else:
                        table_row[gc_phase] = d_data[label][bm_gc][gc_phase]
    l_table = add_line_column(l_table, 1)
    return pandas.DataFrame(l_table)


# =============================== HELPER METHOD ============================== #


def split_analysis(l_analysis: List) -> [List, List, List]:
    l_base_analysis = list()
    l_sampled_analysis = list()
    l_all_analysis = list()
    for d_analysis in l_analysis:
        if d_analysis["title"].startswith("sa-"):
            l_sampled_analysis.append(d_analysis)
        elif d_analysis["title"].startswith("all-"):
            l_all_analysis.append(d_analysis)
        else:
            l_base_analysis.append(d_analysis)
    return {
        "base": l_base_analysis,
        "sampled": l_sampled_analysis,
        "all": l_all_analysis,
    }
