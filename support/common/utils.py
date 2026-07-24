import codecs
import glob
import gzip
import json
import os
import re
import regex
import shutil
import socket
import sys
import tarfile
import yaml

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

from common import check, progress
from common.simulation import counter_utils


class Instrument(Enum):
    COUNTER = 1
    SIMULATION = 2
    SPEC = 3
    JVM = 4


class ExecutionType(Enum):
    AGENT = 1
    GROUP = 2
    UNKNOWN = 3


# Reference -> https://death.andgravity.com/yaml-unknown-tag
def yaml_common_loader() -> None:
    common_loader = yaml.SafeLoader
    common_loader.add_constructor(
        "tag:yaml.org,2002:python/object:common.check.Column",
        check.Column.yaml_constructor,
    )
    common_loader.add_constructor(
        "tag:yaml.org,2002:python/object/apply:common.check.Status",
        check.Status.yaml_constructor,
    )
    common_loader.add_constructor(
        "tag:yaml.org,2002:python/object/apply:common.check.ColumnType",
        check.ColumnType.yaml_constructor,
    )
    common_loader.add_constructor(
        "tag:yaml.org,2002:python/object:common.simulation.counter_utils.Counter",
        counter_utils.Counter.yaml_constructor,
    )
    common_loader.add_constructor(
        "tag:yaml.org,2002:python/object:common.simulation.counter_utils.DistributionCounter",
        counter_utils.DistributionCounter.yaml_constructor,
    )
    common_loader.add_constructor(
        "tag:yaml.org,2002:python/object:common.simulation.counter_utils.StaticCounter",
        counter_utils.StaticCounter.yaml_constructor,
    )
    return common_loader


def parse_yaml(p_yaml: str) -> "yaml.YAMLObject":
    with CommonFile(p_yaml, "r") as f_yaml:
        yaml_obj = yaml.load(f_yaml, Loader=yaml_common_loader())
        return yaml_obj


def save_yaml(yaml_obj: "yaml.YAMLObject", p_yaml: str) -> None:
    f_yaml = open(p_yaml, "w")
    yaml.dump(yaml_obj, f_yaml)
    f_yaml.close()


def parse_json(p_json: str) -> Dict:
    with CommonFile(p_json, "r") as f_json:
        d_json = json.load(f_json)
        return d_json


def save_json(d_json: Dict, p_json: str) -> None:
    f_json = open(p_json, "w")
    json.dump(d_json, f_json, indent=2)
    f_json.close()


def create_output_folder(
    p_output: str, p_tmp: str, l_benchmark: List[str], s_append: str = None
) -> str:
    curr_time = datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
    if p_tmp is not None:
        if not os.path.exists(p_tmp):
            os.makedirs(p_tmp)
        p_tmp_folder = p_tmp + "/" + curr_time
        os.makedirs(p_tmp_folder)
    else:
        p_tmp_folder = None
    if not os.path.exists(p_output):
        os.makedirs(p_output)
    p_output_folder = p_output + "/" + curr_time
    if s_append is not None:
        p_output_folder += "-" + s_append
    os.makedirs(p_output_folder)
    for benchmark in l_benchmark:
        os.makedirs(f"{p_output_folder}/{benchmark}")
    return p_output_folder, p_tmp_folder


def fail_safe_substring(curr_str: str, start_idx: int, end_idx: int) -> str:
    if start_idx == end_idx:
        return ""
    return curr_str[start_idx:end_idx]


def obj_replace_token(val: str, tokens: Dict) -> bool:
    for tk in tokens.keys():
        if f"@{tk}" == val:
            return True, tokens[tk]
    return False, None


def str_replace_tokens(curr_val: str, tokens: Dict) -> str:
    potential_tokens = list(re.finditer(r"@[A-Z]+", curr_val))
    if len(potential_tokens) == 0:
        return curr_val
    can_swap_values, new_val = obj_replace_token(curr_val, tokens)
    if can_swap_values is True:
        return new_val
    new_val = ""
    curr_pos = 0
    for potential_token in potential_tokens:
        new_val += fail_safe_substring(curr_val, curr_pos, potential_token.span()[0])
        tk = potential_token.group()[1:]
        if tk in tokens:
            if type(tokens[tk]) is str:
                new_val += tokens[tk]
            elif type(tokens[tk]) is int or type(tokens[tk]) is float:
                new_val += str(tokens[tk])
            else:
                raise Exception(
                    f"ERROR: Cannot replace {curr_val} with value of type {type(tokens[tk])}"
                )
        else:
            new_val += f"@{tk}"
        curr_pos = potential_token.span()[1]
    new_val += fail_safe_substring(curr_val, curr_pos, len(curr_val))
    return new_val


def dict_replace_tokens(curr_dict: Dict, tokens: Dict) -> Dict:
    new_dict = dict()
    if type(curr_dict) is dict:
        for k in curr_dict.keys():
            v = curr_dict[k]
            if type(v) is dict:
                v = dict_replace_tokens(v, tokens)
            elif type(v) is list:
                for idx in range(len(v)):
                    v[idx] = str_replace_tokens(v[idx], tokens)
            elif type(v) is str:
                v = str_replace_tokens(v, tokens)
            k = str_replace_tokens(k, tokens)
            new_dict[k] = v
        return new_dict
    raise Exception("ERROR: Unknown type")


def move_config_includes(p_running_configs: str, tokens: Dict) -> None:
    running_configs = list(glob.glob(f"{p_running_configs}/*.yaml"))
    set_includes = set()
    for running_config in running_configs:
        y_config = parse_yaml(running_config)
        if "includes" in y_config:
            set_includes = set_includes or set(list(y_config["includes"]))
    config_new_location = dict()
    if len(set_includes) == 0:
        return
    p_includes_running = f"{p_running_configs}/includes"
    os.makedirs(p_includes_running)
    for included_config in set_includes:
        p_new_path = f"{p_includes_running}/{included_config.split('/')[-1]}"
        config_new_location[included_config] = p_new_path
        include_config = dict_replace_tokens(parse_yaml(included_config), tokens)
        save_yaml(include_config, p_new_path)
    for running_config in running_configs:
        y_config = parse_yaml(running_config)
        if "includes" in y_config:
            included_files = list(y_config["includes"])
            new_included_files = list()
            for included_config in included_files:
                new_included_files.append(config_new_location[included_config])
            y_config["includes"] = new_included_files
            save_yaml(y_config, running_config)


def check_file_has_strings(p_file: str, query_strings: List) -> bool:
    query_count = count_string_instances(p_file, query_strings)
    query_bool = [False] * len(query_count)
    for idx in range(len(query_bool)):
        query_bool[idx] = query_count[idx] > 0
    return query_bool


def count_string_instances(
    p_file: str, query_strings: List, starts_with: bool = False
) -> bool:
    query_count = [0] * len(query_strings)
    if os.path.isfile(p_file) == False:
        return query_count
    with CommonFile(p_file, "r") as f_log:
        for log_line in f_log:
            for idx, query in enumerate(query_strings):
                if query in log_line:
                    query_count[idx] += 1
                    if starts_with == True:
                        if log_line.startswith(query) == False:
                            query_count[idx] -= 1
    return query_count


def write_to_file(write_str: str, p_file: str) -> None:
    f_file = open(p_file, "w")
    f_file.write(write_str)
    f_file.close()


def initialize_dict(l_keys: List, init_value: int) -> Dict:
    d_data = dict()
    for k in l_keys:
        d_data[k] = init_value
    return d_data


def generate_bit_mask(cpu_list: List[int], num_cpus: str):
    mask = 0 << int(num_cpus)
    for cpu in cpu_list:
        mask = mask | (1 << cpu)
    return mask


class CommonFile:
    def __init__(self, p_path: str, mode: str):
        self.path = p_path
        self.mode = mode
        self.is_gz = False

    def __enter__(self):
        self.f_support = None
        if self.path.split(".")[-1] == "gz":
            # gzip can ready in "rb" -> read binary, or "rt" -> read text
            self.f_support = gzip.open(self.path, self.mode + "t")
            self.is_gz = True
        else:
            self.f_support = codecs.open(
                self.path, self.mode, encoding="utf-8", errors="ignore"
            )
        return self.f_support

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.f_support.close()

    def __iter__(self):
        return self.f_support

    def __next__(self):
        return self.f_support.readline()


def make_shell_executable(p_file: str) -> None:
    file_mode = os.stat(p_file).st_mode
    file_mode |= (file_mode & 0o444) >> 2
    os.chmod(p_file, file_mode)


def create_folder_if_not_exist(p_dir: str) -> None:
    if not os.path.isdir(p_dir):
        os.makedirs(p_dir)


def archive_contents(p_dir: str) -> None:
    if len(list(os.listdir(p_dir))) == 0:
        return
    curr_time = datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
    p_archive = f"{p_dir}/archive-{curr_time}"
    ignore_archive = shutil.ignore_patterns(p_archive)
    shutil.copytree(p_dir, p_archive, ignore=ignore_archive)
    for p_name in os.listdir(p_dir):
        p_path = os.path.join(p_dir, p_name)
        if p_archive == p_path:
            continue
        if os.path.isfile(p_path):
            os.remove(p_path)
        elif os.path.isdir(p_path):
            shutil.rmtree(p_path)


def create_folder_if_not_exist_and_archive_existing_files(p_dir: str) -> None:
    create_folder_if_not_exist(p_dir)
    archive_contents(p_dir)


def convert_list_of_dict_to_dict_of_lists(l_data: str) -> Dict:
    if len(l_data) == 0:
        return l_data[0]
    l_cols = list(l_data[0].keys())
    d_output = dict()
    for col in l_cols:
        d_output[col] = [None] * len(l_data)
    for idx in range(len(l_data)):
        d_data = l_data[idx]
        for k in d_data.keys():
            d_output[k][idx] = d_data[k]
    return d_output


def combine_yaml_to_list(l_yamls: List) -> List:
    for p_yaml in l_yamls:
        l_yamls.append(parse_yaml(p_yaml))
    return l_yamls


def wipe_log(p_log: str) -> None:
    f_log = open(p_log, "w")
    f_log.write("")
    f_log.close()


def get_currdir() -> str:
    p_curr = os.getcwd()
    p_curr = p_curr.replace("/srv/local", "")
    return p_curr


def get_regex_matches(s_str: str, regex_exp: Any) -> [List, None]:
    regex_matches = regex.search(regex_exp, s_str)
    if regex_matches is None:
        return None
    l_matches = list()
    for group_id in range(1, len(regex_matches.groups()) + 1):
        l_matches += regex_matches.captures(group_id)
    return l_matches


def list_files(p_outdir: str) -> List:
    l_dir = list()
    d_path = dict()
    for p_dir in os.listdir(p_outdir):
        if os.path.isfile(os.path.join(p_outdir, p_dir)):
            if (
                p_dir != "excel"
                and p_dir != "cacti"
                and "archive-" not in p_dir
                and p_dir != "scale"
            ):
                l_dir.append(p_dir)
                assert p_dir not in d_path
                d_path[p_dir] = f"{p_outdir}/{p_dir}"
    return l_dir, d_path


def list_subfolders(p_outdir: str, sort_list: bool = False) -> [List, Dict]:
    l_dir = list()
    d_path = dict()
    for p_dir in os.listdir(p_outdir):
        if os.path.isdir(os.path.join(p_outdir, p_dir)):
            if (
                p_dir != "excel"
                and p_dir != "cacti"
                and "archive-" not in p_dir
                and p_dir != "scale"
                and p_dir != "running"
            ):
                l_dir.append(p_dir)
                assert p_dir not in d_path
                d_path[p_dir] = f"{p_outdir}/{p_dir}"
    if sort_list == True:
        l_dir_sorted = list()
        for p_dir in l_dir:
            if "x" in p_dir:
                found_times = True
            try:
                if found_times == True:
                    p_dir = p_dir.replace("x", "")
                p_dir = float(p_dir)
            except ValueError:
                print(f"{p_dir} cannot be converted to a float")
            l_dir_sorted.append(p_dir)
        l_dir_sorted.sort()
        l_dir.clear()
        for f_dir in l_dir_sorted:
            if found_times == True:
                l_dir.append(f"{f_dir}x")
            else:
                l_dir.append(f_dir)
    return l_dir, d_path


def find_subfolder_type(d_subdir: Dict) -> Dict:
    d_dir_type = dict()
    for p_dir in d_subdir.keys():
        d_dir_type[p_dir] = {
            "path": d_subdir[p_dir],
            "type": ExecutionType.UNKNOWN,
        }
        p_config = f"{d_subdir[p_dir]}/config.yaml"
        if "group-" in p_dir:
            d_dir_type[p_dir]["type"] = ExecutionType.GROUP
        elif os.path.exists(p_config) == True:
            config = parse_yaml(p_config)
            if "counter" in config and config["counter"]["agent"] in {
                "agent",
                "per_phase_agent",
            }:
                d_dir_type[p_dir]["type"] = ExecutionType.AGENT
    return d_dir_type


def get_calling_instrument() -> "Instrument":
    s_instrument = os.path.basename(get_currdir()).lower()
    if s_instrument == "counter":
        return Instrument.COUNTER
    if s_instrument == "simulation":
        return Instrument.SIMULATION
    assert False


def compare_dict_keys(d_A: Dict, d_B: Dict) -> bool:
    l_A = list(d_A.keys())
    l_B = list(d_B.keys())
    l_A.sort()
    l_B.sort()
    return l_A == l_B


def copy_running_ng_config(p_output: str, p_config: str, tokens: Dict) -> str:
    p_running = f"{p_output}/running"
    os.makedirs(p_running, exist_ok=True)
    p_running_configs = f"{p_running}/configs"
    os.makedirs(p_running_configs)
    running_config = parse_yaml(p_config)
    running_config = dict_replace_tokens(running_config, tokens)
    save_yaml(running_config, f"{p_running_configs}/running.yaml")
    move_config_includes(p_running_configs, tokens)
    return f"{p_running_configs}/running.yaml"


def get_cpu_governor(l_cpus: List, expected: str) -> [Dict, bool]:
    b_expected = True
    d_governors = dict()
    for cpu in l_cpus:
        p_scaling = f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_governor"
        with CommonFile(p_scaling, "r") as f_scaling:
            s_scaling = f_scaling.read().strip()
            b_expected = b_expected and (s_scaling == expected)
            d_governors[cpu] = s_scaling
    return d_governors, b_expected


def compare_dict(d_A: Dict, d_B: Dict) -> bool:
    if isinstance(d_A, dict) == False:
        print(f"Not a dict -> {d_A}")
        return False
    if isinstance(d_B, dict) == False:
        print(f"Not a dict -> {d_B}")
        return False
    if compare_dict_keys(d_A, d_B) == False:
        print(f"Keys are unequal -> {d_A.keys()} != {d_B.keys()}")
        return False
    b_equal = True
    for k in d_A.keys():
        if isinstance(d_A[k], dict) == True:
            b_equal = b_equal & compare_dict(d_A[k], d_B[k])
        elif d_A[k] != d_B[k]:
            print(f"Unequal for key {k} -> {d_A[k]} != {d_B[k]}")
            return False
    return b_equal
