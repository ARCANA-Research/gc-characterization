from collections.abc import Callable
from prettytable import PrettyTable
from typing import Dict, List

from common import check, utils


def get_group_colors(p_status: str) -> Dict:
    d_events = check.generate_event_status_dict(p_status, False)
    d_group_colors = dict()
    for column in d_events:
        d_group_colors[column.cgroup] = column.ccolor
    return d_group_colors


def get_table_fields(p_status: str, d_group_colors: Dict, enable_color: bool) -> List:
    d_events = check.generate_event_status_dict(p_status, False)
    table_fields = ["Benchmark", "GC", "Heap"]
    l_columns = ["Benchmark", "GC", "Heap"]
    for column in d_events:
        column_name = column.cname.replace("_", " ")
        column_color = d_group_colors[column.cgroup]
        l_columns.append(column_name)
        if enable_color == True:
            table_fields.append(f"\033[{column_color}m{column_name}\033[0m")
        else:
            table_fields.append(column_name)
    return l_columns, table_fields


def get_table_title(p_status: str, d_group_colors: Dict, enable_color: bool) -> str:
    y_status = utils.parse_yaml(p_status)
    l_groups = list()
    for group in y_status.keys():
        group = group.upper()
        if group != "OK":
            if enable_color == True:
                l_groups.append(f"\033[{d_group_colors[group]}m{group}\033[0m")
            else:
                l_groups.append(group)
    return f"Execution Status ({', '.join(l_groups)})"


def parse_table_values(table_row: List, enable_color: bool) -> str:
    l_output = list()
    for cell_value in table_row:
        if isinstance(cell_value, check.Status):
            if cell_value == check.Status.PASSED:
                if enable_color == True:
                    l_output.append("\033[32m\u25A0\033[0m")
                else:
                    l_output.append("\u2714")
            elif cell_value == check.Status.FAILED:
                if enable_color == True:
                    l_output.append("\033[31m\u25A0\033[0m")
                else:
                    l_output.append("\u2718")
            elif cell_value == check.Status.UNKNOWN:
                if enable_color == True:
                    l_output.append("\033[33m\u25A0\033[0m")
                else:
                    l_output.append("\u2610")
            else:
                if enable_color == True:
                    l_output.append("\033[30m\u25A0\033[0m")
                else:
                    l_output.append("\u2610")
        else:
            l_output.append(str(cell_value))
    return " ".join(l_output)


def get_table_row_values(l_columns: List, d_data_row: Dict) -> str:
    table_row = [""] * len(l_columns)
    assert len(table_row) - 3 == len(d_data_row.keys())
    d_columns = dict()
    for col_idx, column in enumerate(l_columns):
        d_columns[column] = col_idx
    for column in d_data_row:
        column_name = column.cname.replace("_", " ")
        table_row[d_columns[column_name]] = d_data_row[column]
    return table_row


def get_table_row(l_columns: List, d_data_row: Dict, enable_color: bool) -> str:
    table_row = get_table_row_values(l_columns, d_data_row)
    for idx in range(len(table_row)):
        table_row[idx] = parse_table_values(table_row[idx], enable_color)
    return table_row


def update_data_base(
    d_base: Dict, d_benchmarks: Dict, split_benchmark_path: Callable
) -> Dict:
    d_data = d_base
    for b_hash in d_benchmarks:
        num_attempts = len(d_benchmarks[b_hash]["EXECUTION"])
        for idx in range(num_attempts):
            d_execution = d_benchmarks[b_hash]["EXECUTION"][idx]
            if d_execution is None:
                continue
            p_benchmark = d_benchmarks[b_hash]["PATHS"][idx]
            bm_name, bm_gc, bm_iteration, bm_heap = split_benchmark_path(p_benchmark)
            for event in d_execution.keys():
                if event == "PROCESS":
                    continue
                event_value = d_execution[event]
                if event.ctype == check.ColumnType.BOOLEAN:
                    d_data[bm_name][bm_gc][bm_heap][event][bm_iteration] = event_value
                else:
                    if isinstance(event_value, check.Status):
                        if (
                            d_execution[event] == check.Status.UNKNOWN
                            or d_execution[event] == check.Status.DISREGARD
                        ):
                            d_data[bm_name][bm_gc][bm_heap][event][bm_iteration] = "."
                        else:
                            assert False
                    else:
                        d_data[bm_name][bm_gc][bm_heap][event][
                            bm_iteration
                        ] = d_execution[event]
    return d_data


def generate_data_base(
    p_status: str,
    d_benchmarks: Dict,
    split_benchmark_path: Callable,
) -> List:
    d_events = check.generate_event_status_dict(p_status, False)
    d_base = dict()
    for b_hash in d_benchmarks:
        num_attempts = len(d_benchmarks[b_hash]["EXECUTION"])
        for idx in range(len(d_benchmarks[b_hash]["EXECUTION"])):
            bm_name, bm_gc, bm_iteration, bm_heap = split_benchmark_path(
                d_benchmarks[b_hash]["PATHS"][idx]
            )
            if bm_name not in d_base:
                d_base[bm_name] = dict()
            if bm_gc not in d_base[bm_name]:
                d_base[bm_name][bm_gc] = dict()
            if bm_heap not in d_base[bm_name][bm_gc]:
                d_base[bm_name][bm_gc][bm_heap] = dict()
            for event in d_events:
                if event == "PROCESS":
                    d_base[bm_name][bm_gc][bm_heap][event] = [
                        d_benchmarks[b_hash]["PROCESS"]
                    ]
                else:
                    d_base[bm_name][bm_gc][bm_heap][event] = [
                        check.Status.UNKNOWN
                    ] * num_attempts
    return d_base


def generate_table(
    d_benchmarks: Dict,
    p_status: str,
    split_benchmark_path: str,
    enable_color: bool,
    iterations: bool,
) -> Dict:
    d_table_base = generate_data_base(p_status, d_benchmarks, split_benchmark_path)
    d_data = update_data_base(d_table_base, d_benchmarks, split_benchmark_path)
    d_group_colors = get_group_colors(p_status)
    l_columns, table_fields = get_table_fields(p_status, d_group_colors, enable_color)
    table = PrettyTable(table_fields)
    table.title = get_table_title(p_status, d_group_colors, enable_color)
    for bm_name in d_data:
        for bm_gc_idx, bm_gc in enumerate(d_data[bm_name].keys()):
            for bm_heap_idx, bm_heap in enumerate(d_data[bm_name][bm_gc].keys()):
                table_row = get_table_row(
                    l_columns, d_data[bm_name][bm_gc][bm_heap], enable_color
                )
                if bm_gc_idx == 0:
                    table_row[0] = bm_name
                if bm_heap_idx == 0:
                    table_row[1] = bm_gc
                table_row[2] = bm_heap
                table.add_row(table_row)
        table.add_row(get_table_spacer(l_columns))
    table.add_row(get_total_count_row(l_columns, d_data, iterations))
    return str(table)


def get_table_spacer(l_columns: List) -> List:
    table_row = list()
    for column in l_columns:
        table_row.append("-" * len(column))
    return table_row


def get_total_count_row(l_columns: List, d_data: Dict, iterations: int) -> List:
    total_executions = 0
    l_event_executions = [None] * len(l_columns)
    start_idx = 4
    for bm_name in d_data:
        for bm_gc in d_data[bm_name]:
            for bm_heap in d_data[bm_name][bm_gc]:
                table_row = get_table_row_values(
                    l_columns, d_data[bm_name][bm_gc][bm_heap]
                )
                total_executions += iterations
                for idx in range(start_idx, len(table_row)):
                    table_col = table_row[idx]
                    assert type(table_col) == list
                    for cell_value in table_col:
                        if isinstance(cell_value, check.Status):
                            if l_event_executions[idx] is None:
                                l_event_executions[idx] = 0
                            if cell_value == check.Status.PASSED:
                                l_event_executions[idx] += 1
                        elif type(cell_value) == int or type(cell_value) == float:
                            if l_event_executions[idx] is None:
                                l_event_executions[idx] = {"total": 0.0, "count": 0}
                            l_event_executions[idx]["total"] += float(cell_value)
                            l_event_executions[idx]["count"] += 1
    table_row = [""] * len(l_columns)
    for idx in range(start_idx, len(table_row)):
        if l_event_executions[idx] is None:
            table_row[idx] = ""
        elif type(l_event_executions[idx]) == dict:
            average_value = l_event_executions[idx]["total"] / float(
                l_event_executions[idx]["count"]
            )
            table_row[idx] = f"{average_value:.2f}"
        else:
            table_row[idx] = f"{l_event_executions[idx]}/{total_executions}"
    return table_row
