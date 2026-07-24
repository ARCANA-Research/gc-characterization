import copy
import numpy

from scipy import stats
from typing import Any, Callable, Dict, List, Union


# Peform operations over scalars
def op_binary(op_A: Any, op_B: Any, f_op: Callable) -> Any:
    if type(op_A) != type(op_B):
        if not isinstance(op_A, (int, float)) or not isinstance(op_B, (int, float)):
            raise RuntimeError(f"ERROR: {type(op_A)} is not the same as {type(op_B)}")
    if isinstance(op_A, dict):
        assert set(op_A.keys()) == set(op_B.keys())
        d_op = dict()
        for k in op_A.keys():
            v_A = op_A[k]
            v_B = op_B[k]
            d_op[k] = op_binary(v_A, v_B, f_op)
        return d_op
    if isinstance(op_A, list):
        assert len(op_A) == len(op_B)
        l_op = list()
        for idx in range(len(op_A)):
            v_A = op_A[idx]
            v_B = op_B[idx]
            l_op.append(op_binary(v_A, v_B, f_op))
        return l_op
    return f_op(op_A, op_B)


# Peform operations over lists
def op_unary(op_A: Any, f_op: Callable) -> Any:
    if isinstance(op_A, dict):
        d_op = dict()
        for k in op_A.keys():
            v_A = op_A[k]
            d_op[k] = op_unary(v_A, f_op)
        return d_op
    if isinstance(op_A, list):
        return f_op(op_A)
    return f_op(op_A)


# Perform operation with constant value
def op_constant(op_A: Any, v_const: Any, f_op: Callable) -> Any:
    if isinstance(op_A, dict):
        d_op = dict()
        for k in op_A.keys():
            v_A = op_A[k]
            d_op[k] = op_constant(v_A, v_const, f_op)
        return d_op
    if isinstance(op_A, list):
        l_op = list()
        for idx in range(len(op_A)):
            v_A = op_A[idx]
            l_op.append(op_constant(v_A, v_const, f_op))
        return l_op
    return f_op(op_A, v_const)


def op_multiply(op_A: int, op_B: int) -> float:
    return float(op_A) * float(op_B)


def op_divide(op_A: int, op_B: int) -> float:
    if op_B == 0:
        return float(0)
    if op_A is None:
        return float(0)
    return float(op_A) / float(op_B)


def op_add(op_A: int, op_B: int) -> float:
    return op_A + op_B


def op_sub(op_A: int, op_B: int) -> float:
    return op_A - op_B


# takes mean across indices for many lists
def op_y_mean(l_vals: list) -> Union[List[float], float]:
    assert len(l_vals) > 0
    l_vals = [v for v in l_vals if v is not None]
    if len(l_vals) == 0:
        return None
    assert isinstance(l_vals[0], list)
    l_mean = list()
    for idx in range(len(l_vals[0])):
        l_idx_vals = [None] * len(l_vals)
        for val_idx in range(len(l_vals)):
            l_idx_vals[val_idx] = l_vals[val_idx][idx]
        l_mean.append(op_mean(l_idx_vals))
    return l_mean


# estimates mean across all lists of for a collection of lists
def op_x_mean(l_vals: list) -> Union[List[float], float]:
    assert len(l_vals) > 0
    l_vals = [v for v in l_vals if v is not None]
    if len(l_vals) == 0:
        return None
    assert isinstance(l_vals[0], list)
    l_mean = list()
    for idx in range(len(l_vals)):
        l_mean.append(op_mean(l_vals[idx]))
    return l_mean


def op_mean(l_vals: list) -> Union[List[float], float]:
    if len(l_vals) == 0:
        return None
    assert len(l_vals) > 0
    l_vals = [v for v in l_vals if v is not None]
    if len(l_vals) == 0:
        return None
    if isinstance(l_vals[0], list):
        print(l_vals)
    assert not isinstance(l_vals[0], list)
    for v in l_vals:
        if v == 0:
            return 0.0
        assert v >= 0
    return stats.gmean(l_vals)


def op_p99(l_vals: list) -> Union[List[float], float]:
    if len(l_vals) == 0:
        return None
    assert len(l_vals) > 0
    l_vals = [v for v in l_vals if v is not None]
    if len(l_vals) == 0:
        return None
    assert not isinstance(l_vals[0], list)
    return numpy.percentile(l_vals, 99)


def op_x_p99(l_vals: list) -> Union[List[float], float]:
    assert len(l_vals) > 0
    l_vals = [v for v in l_vals if v is not None]
    if len(l_vals) == 0:
        return None
    assert isinstance(l_vals[0], list)
    l_p99 = list()
    for idx in range(len(l_vals)):
        l_p99.append(op_p99(l_vals[idx]))
    return l_p99


def op_remove_zero(l_vals: list) -> List[float]:
    assert isinstance(l_vals, list)
    if len(l_vals) == 0:
        return list()
    if isinstance(l_vals[0], list):
        l_remove = list()
        for idx in range(len(l_vals)):
            l_remove.append(op_remove_zero(l_vals[idx]))
        return l_remove
    assert not isinstance(l_vals[0], list)
    l_vals = [v for v in l_vals if v != 0]
    return l_vals


def op_remove_none(l_vals: list) -> List[float]:
    assert isinstance(l_vals, list)
    if len(l_vals) == 0:
        return list()
    if isinstance(l_vals[0], list):
        l_remove = list()
        for idx in range(len(l_vals)):
            l_remove.append(op_remove_none(l_vals[idx]))
        return l_remove
    assert not isinstance(l_vals[0], list)
    l_vals = [v for v in l_vals if v is not None]
    return l_vals


def op_remove_negative(l_vals: list) -> List[float]:
    assert isinstance(l_vals, list)
    if len(l_vals) == 0:
        return list()
    if isinstance(l_vals[0], list):
        l_remove = list()
        for idx in range(len(l_vals)):
            l_remove.append(op_remove_negative(l_vals[idx]))
        return l_remove
    assert not isinstance(l_vals[0], list)
    l_vals = [v for v in l_vals if v >= 0]
    return l_vals


def op_merge_continuous_values(l_vals: list) -> List[float]:
    assert isinstance(l_vals, list)
    if len(l_vals) == 0:
        return list()
    if isinstance(l_vals[0], list):
        l_merge = list()
        for idx in range(len(l_vals)):
            l_merge.append(op_merge_continuous_values(l_vals[idx]))
        return l_merge
    assert not isinstance(l_vals[0], list)
    for idx in range(len(l_vals) - 1):
        if (
            l_vals[idx] is not None
            and l_vals[idx + 1] is not None
            and l_vals[idx] > 0
            and l_vals[idx + 1] > 0
        ):
            l_vals[idx + 1] += l_vals[idx]
            l_vals[idx] = None
    return l_vals


# estimates average across all lists of for a collection of lists
def op_x_average(l_vals: list) -> Union[List[float], float]:
    assert len(l_vals) > 0
    l_vals = [v for v in l_vals if v is not None]
    if len(l_vals) == 0:
        return None
    assert isinstance(l_vals[0], list)
    l_mean = list()
    for idx in range(len(l_vals)):
        l_mean.append(op_average(l_vals[idx]))
    return l_mean


def op_average(l_vals: list) -> Union[List[float], float]:
    if l_vals is None:
        return None
    if len(l_vals) == 0:
        return None
    assert len(l_vals) > 0
    l_vals = [v for v in l_vals if v is not None]
    if len(l_vals) == 0:
        return None
    assert not isinstance(l_vals[0], list)
    return numpy.mean(l_vals)


def op_change_percent(new_val: int, old_val: int) -> float:
    return (float(new_val) - float(old_val)) / float(old_val)


def op_change_percent_inverse(new_val: int, old_val: int) -> float:
    return (float(old_val) - float(new_val)) / float(old_val)


def generate_hash_idx_map(l_A: List, op_hash: Callable) -> Dict:
    d_hash_A = dict()
    for idx_A in range(len(l_A)):
        b_hash_idx = op_hash(l_A[idx_A])
        assert b_hash_idx not in d_hash_A
        d_hash_A[b_hash_idx] = idx_A
    return d_hash_A


def op_lists_with_hash(
    l_A: List, l_B: List, op_func: Callable, op_hash: Callable
) -> List:
    if len(l_A) == 0:
        return l_B
    if len(l_B) == 0:
        return l_A
    d_hash_A = generate_hash_idx_map(l_A, op_hash)
    d_hash_B = generate_hash_idx_map(l_B, op_hash)
    d_hash_total = set(d_hash_A.keys()).union(set(d_hash_B.keys()))
    l_op = list()
    for b_hash in d_hash_total:
        d_op = None
        if b_hash in d_hash_A:
            idx_A = d_hash_A[b_hash]
            d_op = copy.deepcopy(l_A[idx_A])
        if b_hash in d_hash_B:
            idx_B = d_hash_B[b_hash]
            if d_op is None:
                d_op = copy.deepcopy(l_B[idx_B])
            else:
                d_op = op_func(d_op, l_B[idx_B])
        assert d_op is not None
        l_op.append(d_op)
    assert len(l_op) == len(d_hash_total)
    return l_op
