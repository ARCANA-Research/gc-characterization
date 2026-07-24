import copy

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from common import op
from common.simulation import parse_utils


class AbstractCounter(ABC):
    @abstractmethod
    def __init__(
        self, name: str, num_phases: int, output_name: str, multiplier: str
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_value(self, phase: int, name: str, **kwargs) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_events(self) -> List:
        raise NotImplementedError

    @abstractmethod
    def __eq__(self, other: Any) -> bool:
        raise NotImplementedError

    @abstractmethod
    def __hash__(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def to_string(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def finished_adding_values(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def drop_idx(self, idx: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def __len__(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def to_yaml(self, drop_multiplier: bool) -> [Any, str]:
        raise NotImplementedError

    @abstractmethod
    def fix_ramulator2(self) -> None:
        return NotImplementedError

    @abstractmethod
    def add_counter(self, other: Any) -> None:
        return NotImplementedError

    @staticmethod
    @abstractmethod
    def yaml_constructor(loader: "yaml.Loader", node: "yaml.Node") -> Any:
        return NotImplementedError

    @abstractmethod
    def merge_gcstw(self, l_move: List) -> None:
        return NotImplementedError

    @abstractmethod
    def get_parse_counter(self, idx: int) -> "AbstractParseCounter":
        return NotImplementedError


class Counter(AbstractCounter):
    def __init__(
        self, name: str, num_phases: int, output_name: str, multiplier: str
    ) -> None:
        self.name = name
        self.data = [0] * num_phases
        self.output_name = output_name
        self.multiplier = multiplier

    def add_value(self, idx: int, name: str, val: str) -> None:
        assert self.name == name
        if "." in val:
            self.data[idx] = float(val)
        else:
            self.data[idx] = int(val)

    def get_events(self) -> List:
        return [self.name]

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            return self.name == other
        if isinstance(other, AbstractCounter):
            return self.name == other.name
        raise NotImplementedError

    def __hash__(self) -> int:
        return hash(self.name)

    def to_string(self) -> str:
        return f"{self.name:<210} -> {self.output_name:<30} | {str(self.data)}"

    def finished_adding_values(self) -> None:
        pass

    def drop_idx(self, idx: int) -> None:
        self.data.pop(idx)

    def __len__(self) -> int:
        return len(self.data)

    def to_yaml(self, drop_multiplier: bool) -> [Any, str]:
        output_obj = copy.deepcopy(self)
        output_obj.name = output_obj.output_name
        del output_obj.output_name
        if drop_multiplier is True:
            del output_obj.multiplier
        return output_obj, output_obj.name

    def fix_ramulator2(self) -> None:
        self.data = fix_ramulator2_counter(self.name, self.data)

    def add_counter(self, other: Any) -> None:
        assert isinstance(other, Counter)
        assert self == other
        self.data = op.op_binary(self.data, other.data, op.op_add)

    @staticmethod
    def yaml_constructor(loader: "yaml.Loader", node: "yaml.Node") -> "Counter":
        counter_name = None
        counter_data = None
        counter_multiplier = None
        for node_pair in node.value:
            key = loader.construct_scalar(node_pair[0])
            if key == "data":
                counter_data = loader.construct_sequence(node_pair[1])
            elif key == "name":
                counter_name = loader.construct_scalar(node_pair[1])
            elif key == "multiplier":
                counter_multiplier = loader.construct_scalar(node_pair[1])
            else:
                assert False
        assert counter_name is not None
        assert counter_data is not None
        output_name = counter_name
        if ")" in counter_name:
            output_name = counter_name.split(")")[-1]
        obj = Counter(counter_name, 0, output_name, counter_multiplier)
        obj.data = counter_data
        return obj

    def merge_gcstw(self, l_move: List) -> None:
        for idx in range(len(l_move)):
            if l_move[idx] is not None:
                self.data[l_move[idx]] += self.data[idx]
                self.data[idx] = None
        self.data = [val for val in self.data if val is not None]

    def get_parse_counter(self, idx: int) -> "ParseCounter":
        return parse_utils.ParseCounter(self.data[idx])


class DistributionCounter(AbstractCounter):
    def __init__(
        self, name: Dict, num_phases: int, output_name: str, multiplier: str
    ) -> None:
        if isinstance(name, str):
            self.name = name
        else:
            self.name = copy.deepcopy(name)
            assert "samples" in self.name
            assert "mean" in self.name or "total" in self.name
            if "mean" not in self.name:
                self.name["mean"] = None
            elif "total" not in self.name:
                self.name["total"] = None
            else:
                assert False
        self.mean = [0.0] * num_phases
        self.samples = [0] * num_phases
        self.total = [0] * num_phases
        self.output_name = output_name
        self.multiplier = multiplier

    def add_value(self, idx: int, name: str, val: str) -> None:
        if name == self.name["mean"]:
            self.mean[idx] = float(val)
        elif name == self.name["samples"]:
            self.samples[idx] = int(val)
        elif name == self.name["total"]:
            self.total[idx] = int(val)
        else:
            assert False

    def get_events(self) -> List:
        l_events = self.name.values()
        return [event for event in l_events if event is not None]

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            assert other is not None
            if isinstance(self.name, dict):
                return other in list(self.name.values())
            return other == self.name
        if isinstance(other, AbstractCounter):
            return self.name == other.name
        raise NotImplementedError

    def __hash__(self) -> int:
        if isinstance(self.name, dict):
            return hash(list(self.name.values()))
        return hash(self.name)

    def to_string(self) -> str:
        return f'{("mean: " + str(self.name["mean"])):<70}{(" | total: " + str(self.name["total"])):<70}{(" | samples: " + str(self.name["samples"])):<70} -> {self.output_name:<30} | mean: {str(self.mean)} | samples: {str(self.samples)} | total: {str(self.total)}'

    def finished_adding_values(self) -> None:
        if self.name["mean"] is not None:
            self.total = op.op_binary(self.mean, self.samples, op.op_multiply)
        self.mean = None

    def drop_idx(self, idx: int) -> None:
        assert self.mean is None
        self.samples.pop(idx)
        self.total.pop(idx)

    def __len__(self) -> int:
        assert self.mean is None
        assert len(self.total) == len(self.samples)
        return len(self.total)

    def to_yaml(self, drop_multiplier: bool) -> [Any, str]:
        output_obj = copy.deepcopy(self)
        output_obj.name = output_obj.output_name
        del output_obj.output_name
        del output_obj.mean
        if drop_multiplier is True:
            del output_obj.multiplier
        return output_obj, output_obj.name

    def fix_ramulator2(self) -> None:
        assert self.mean is None
        self.total = fix_ramulator2_counter(self.name, self.total)
        self.samples = fix_ramulator2_counter(self.name, self.samples)

    def add_counter(self, other: Any) -> None:
        assert isinstance(other, DistributionCounter)
        assert self == other
        self.total = op.op_binary(self.total, other.total, op.op_add)
        self.samples = op.op_binary(self.samples, other.samples, op.op_add)

    @staticmethod
    def yaml_constructor(
        loader: "yaml.Loader", node: "yaml.Node"
    ) -> "DistributionCounter":
        counter_name = None
        counter_total = None
        counter_samples = None
        counter_multiplier = None
        for node_pair in node.value:
            key = loader.construct_scalar(node_pair[0])
            if key == "total":
                counter_total = loader.construct_sequence(node_pair[1])
            elif key == "samples":
                counter_samples = loader.construct_sequence(node_pair[1])
            elif key == "name":
                counter_name = loader.construct_scalar(node_pair[1])
            elif key == "multiplier":
                counter_multiplier = loader.construct_scalar(node_pair[1])
            else:
                assert False
        assert counter_name is not None
        assert counter_total is not None
        assert counter_samples is not None
        output_name = counter_name
        if ")" in counter_name:
            output_name = counter_name.split(")")[-1]
        obj = DistributionCounter(counter_name, 0, output_name, counter_multiplier)
        obj.total = counter_total
        obj.samples = counter_samples
        obj.mean = None
        return obj

    def merge_gcstw(self, l_move: List) -> None:
        for idx in range(len(l_move)):
            if l_move[idx] is not None:
                self.total[l_move[idx]] += self.total[idx]
                self.total[idx] = None
                self.samples[l_move[idx]] += self.samples[idx]
                self.samples[idx] = None
        self.total = [val for val in self.total if val is not None]
        self.samples = [val for val in self.samples if val is not None]

    def get_parse_counter(self, idx: int) -> "ParseDistributionCounter":
        return parse_utils.ParseDistributionCounter(self.total[idx], self.samples[idx])


class StaticCounter(AbstractCounter):
    def __init__(
        self, name: str, num_phases: int, output_name: str, multiplier: str
    ) -> None:
        self.name = name
        self.data = [0] * num_phases
        self.output_name = output_name
        self.multiplier = multiplier

    def add_value(self, idx: int, name: str, val: str) -> None:
        assert self.name == name
        self.data[idx] = int(val)

    def get_events(self) -> List:
        return [self.name]

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            return self.name == other
        if isinstance(other, AbstractCounter):
            return self.name == other.name
        raise NotImplementedError

    def __hash__(self) -> int:
        return hash(self.name)

    def to_string(self) -> str:
        return f"{self.name:<210} -> {self.output_name:<30} | {str(self.data)}"

    def finished_adding_values(self) -> None:
        pass

    def drop_idx(self, idx: int) -> None:
        self.data.pop(idx)

    def __len__(self) -> int:
        return len(self.data)

    def to_yaml(self, drop_multiplier: bool) -> [Any, str]:
        output_obj = copy.deepcopy(self)
        output_obj.name = output_obj.output_name
        del output_obj.output_name
        if drop_multiplier is True:
            del output_obj.multiplier
        return output_obj, output_obj.name

    def fix_ramulator2(self) -> None:
        pass

    def add_counter(self, other: Any) -> None:
        assert False  # cannot add to static counter

    @staticmethod
    def yaml_constructor(loader: "yaml.Loader", node: "yaml.Node") -> "StaticCounter":
        counter_name = None
        counter_data = None
        counter_multiplier = None
        for node_pair in node.value:
            key = loader.construct_scalar(node_pair[0])
            if key == "data":
                counter_data = loader.construct_sequence(node_pair[1])
            elif key == "name":
                counter_name = loader.construct_scalar(node_pair[1])
            elif key == "multiplier":
                counter_multiplier = loader.construct_scalar(node_pair[1])
            else:
                assert False
        assert counter_name is not None
        assert counter_data is not None
        output_name = counter_name
        if ")" in counter_name:
            output_name = counter_name.split(")")[-1]
        obj = StaticCounter(counter_name, 0, output_name, counter_multiplier)
        obj.data = counter_data
        return obj

    def merge_gcstw(self, l_move: List) -> None:
        for idx in range(len(l_move)):
            if l_move[idx] is not None:
                self.data[idx] = None
        self.data = [val for val in self.data if val is not None]

    def get_parse_counter(self, idx: int) -> "ParseStaticCounter":
        return parse_utils.ParseStaticCounter(self.data[idx])


def get_counter_name(counter: Dict, multiplier: int, counter_key: str) -> Dict:
    multiplier = "" if multiplier is None else multiplier
    separator = counter.get("separator", "")
    append = counter.get("append", "")
    base = counter.get("base", None)
    output_name = (
        f"({counter_key}){counter['name']}"
        if counter_key is not None
        else counter["name"]
    )
    event_name = (
        counter["event"][counter_key] if counter_key is not None else counter["event"]
    )
    if isinstance(event_name, dict):
        d_counter_name = dict()
        for k in event_name:
            if base is not None:
                d_counter_name[
                    k
                ] = f"{base}{multiplier}{separator}{event_name[k]}{append}"
            else:
                d_counter_name[k] = f"{event_name[k]}{multiplier}{append}"
        return {"counter_name": d_counter_name, "output_name": output_name}
    else:
        if base is not None:
            return {
                "counter_name": f"{base}{multiplier}{separator}{event_name}{append}",
                "output_name": output_name,
            }
        else:
            return {
                "counter_name": f"{event_name}{multiplier}{append}",
                "output_name": output_name,
            }


def get_counter_list(counter: Dict, multiplier: int, num_phases: int) -> List:
    l_counter_names = list()
    if isinstance(counter["event"], dict) and "gc" in counter["event"]:
        l_counter_key = list(counter["event"].keys())
        l_counter_key.sort()
        assert ["gc", "nongc"] == l_counter_key
        for k in l_counter_key:
            l_counter_names.append(get_counter_name(counter, multiplier, k))
    else:
        l_counter_names.append(get_counter_name(counter, multiplier, None))
    l_counters = list()
    for counter_def in l_counter_names:
        counter_name = counter_def["counter_name"]
        output_name = counter_def["output_name"]
        if counter["type"] == "counter":
            l_counters.append(
                Counter(counter_name, num_phases, output_name, multiplier)
            )
        elif counter["type"] == "distribution":
            l_counters.append(
                DistributionCounter(counter_name, num_phases, output_name, multiplier)
            )
    return l_counters


def print_counter_list(l_counters: List) -> None:
    for counter in l_counters:
        print(counter.to_string())


def fix_ramulator2_counter(
    counter_name: str, l_vals: List, check_energy: bool = True
) -> List:
    l_fixed_vals = [0] * len(l_vals)
    if len(l_vals) > 0:
        l_fixed_vals[0] = 0
    for idx in range(1, len(l_vals)):
        l_fixed_vals[idx] = op.op_sub(l_vals[idx], l_vals[idx - 1])
        if l_fixed_vals[idx] < 0:
            if abs(l_fixed_vals[idx]) < 0.001:
                print(
                    f"Changing negative value ({counter_name}): {l_fixed_vals[idx]} to 0"
                )
                l_fixed_vals[idx] = 0
            else:
                print(
                    f"ERROR: Too high negative value ({counter_name}): {l_fixed_vals[idx]}"
                )
                assert False
    if "energy" in counter_name and check_energy == True:
        l_fixed_vals = fix_ramulator2_counter(
            counter_name, l_fixed_vals, check_energy=False
        )
    return l_fixed_vals


def counters_list_to_yaml(l_counters: List, sum_same_counters: bool) -> List:
    l_yaml = list()
    for counter in l_counters:
        counter_obj, counter_name = counter.to_yaml(sum_same_counters)
        if counter_name in l_yaml and sum_same_counters == True:
            counter_idx = l_yaml.index(counter_name)
            l_yaml[counter_idx].add_counter(counter_obj)
        else:
            l_yaml.append(counter_obj)
    return l_yaml
