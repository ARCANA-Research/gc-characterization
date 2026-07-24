from abc import ABC, abstractmethod
from typing import Any, Dict, Union


class AbstractParseCounter(ABC):
    @abstractmethod
    def __init__(self, **kwargs: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def to_string(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def add_counter(self, other: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def divide_counter(self, other: Any) -> None:
        # currently not planned to be used
        raise NotImplementedError

    # @abstractmethod
    # def assert_zero(self) -> None:
    #     raise NotImplementedError

    @abstractmethod
    def finalize(self) -> Union[int, float]:
        raise NotImplementedError


class ParseCounter(AbstractParseCounter):
    def __init__(self, data: Union[int, float]) -> None:
        self.data = data

    def to_string(self) -> str:
        return str(self.data)

    def add_counter(self, other: Any) -> None:
        assert isinstance(other, ParseCounter)
        self.data += other.data

    def divide_counter(self, other: Any) -> None:
        assert isinstance(other, ParseCounter)
        self.data /= other.data

    # def assert_zero(self) -> None:
    #     assert self.data == 0

    def finalize(self) -> Union[int, float]:
        return self.data


class ParseDistributionCounter(AbstractParseCounter):
    def __init__(self, total: Union[int, float], samples: int) -> None:
        self.total = total
        self.samples = samples

    def to_string(self) -> str:
        return f"total: {str(self.total)} | samples: {str(self.samples)}"

    def add_counter(self, other: Any) -> None:
        assert isinstance(other, ParseDistributionCounter)
        self.total += other.total
        self.samples += other.samples

    def add_counter(self, other: Any) -> None:
        assert isinstance(other, ParseDistributionCounter)
        self.total += other.total
        self.samples += other.samples

    def divide_counter(self, other: Any) -> None:
        # currently not planned to be used
        assert False

    # def assert_zero(self) -> None:
    #     assert self.total == 0
    #     assert self.samples == 0

    def finalize(self) -> float:
        if self.samples == 0:
            return 0.0
        return float(self.total) / float(self.samples)


class ParseStaticCounter(AbstractParseCounter):
    def __init__(self, data: Union[int, float]) -> None:
        self.data = data

    def to_string(self) -> str:
        return str(self.data)

    def add_counter(self, other: Any) -> None:
        assert isinstance(other, ParseStaticCounter)
        self.data = other.data

    def divide_counter(self, other: Any) -> None:
        # currently not planned to be used
        assert False

    # def assert_zero(self) -> None:
    #     assert self.data == 0
    #     assert self.data == 0

    def finalize(self) -> Union[int, float]:
        return self.data


def get_empty_counter(example_obj: "AbstractParseCounter") -> "AbstractParseCounter":
    if isinstance(example_obj, ParseCounter):
        return ParseCounter(0)
    if isinstance(example_obj, ParseDistributionCounter):
        return ParseDistributionCounter(0, 0)
    if isinstance(example_obj, ParseStaticCounter):
        return ParseStaticCounter(0)
    assert False


def print_parse_dict(d_parse: Dict) -> None:
    for k in d_parse.keys():
        print(f"{k} -> {d_parse[k].to_string()}")
