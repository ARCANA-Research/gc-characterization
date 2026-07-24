import inspect
import isodate
import json
import os
import subprocess
import sys

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List

from common import op, jvm, utils

DACAPO_JFR_EVENT = "DacapoChopinCallback$DaCapoJfr"


def check_jfr_roi_markers(config: "yaml.YAMLObject", p_jfr: str) -> bool:
    p_jfr_bin = f"{jvm.get_jvm_path(config)}/bin/jfr"
    p = subprocess.run(
        [p_jfr_bin, "print", "--json", "--events", DACAPO_JFR_EVENT, p_jfr],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    if p.stderr:  # make sure stderr is empty
        return False
    d_jfr = json.loads(p.stdout.decode("utf-8"))
    l_dacapo = d_jfr["recording"]["events"]
    if len(l_dacapo) != 2:  # start and end ROI
        return False
    if l_dacapo[0]["type"] != DACAPO_JFR_EVENT:
        return False
    if l_dacapo[1]["type"] != DACAPO_JFR_EVENT:
        return False
    if l_dacapo[0]["values"]["roiStart"] != True:
        return False
    if l_dacapo[0]["values"]["roiEnd"] != False:
        return False
    if l_dacapo[1]["values"]["roiStart"] != False:
        return False
    if l_dacapo[1]["values"]["roiEnd"] != True:
        return False
    return True


def get_jfr_json_path(config: "yaml.YAMLObject", p_jfr: str) -> str:
    p_jfr_json = p_jfr.replace(".jfr", "_jfr.json")
    if not os.path.isfile(p_jfr_json):
        print(f"Generating JSON JFR -> {p_jfr_json}")
        f_jfr_json = open(p_jfr_json, "w")
        p_jfr_bin = f"{jvm.get_jvm_path(config)}/bin/jfr"
        p = subprocess.run(
            [p_jfr_bin, "print", "--json", p_jfr],
            stdout=f_jfr_json,
            stderr=subprocess.PIPE,
            check=True,
        )
        assert not p.stderr  # make sure stderr is empty
        f_jfr_json.close()
    return p_jfr_json


def get_event_map() -> Dict:
    d_jfr_event = dict()
    for _, class_def in inspect.getmembers(sys.modules[__name__]):
        if inspect.isclass(class_def):
            if issubclass(class_def, AbstractEvent) and class_def != AbstractEvent:
                d_jfr_event[class_def.get_name()] = class_def
    return d_jfr_event


def get_jfr_event_objects(d_jfr_map: Dict, p_jfr_json: str) -> List:
    l_events = list()
    d_jfr = utils.parse_json(p_jfr_json)
    in_roi = False
    for d_event in d_jfr["recording"]["events"]:
        if in_roi == False:
            if d_event["type"] == DACAPO_JFR_EVENT:
                assert d_event["values"]["roiStart"] == True
                assert d_event["values"]["roiEnd"] == False
                in_roi = True
        else:
            if d_event["type"] == DACAPO_JFR_EVENT:
                assert d_event["values"]["roiStart"] == False
                assert d_event["values"]["roiEnd"] == True
                in_roi = False
            else:
                assert d_event["type"] in d_jfr_map
                l_events.append(d_jfr_map[d_event["type"]].from_json(d_event))
    return l_events


class GCWhen(Enum):
    BEFORE_GC = 1
    AFTER_GC = 2

    @staticmethod
    def from_string(s: str) -> "GCWhen":
        if s == "Before GC":
            return GCWhen.BEFORE_GC
        if s == "After GC":
            return GCWhen.AFTER_GC
        assert False


class AbstractEvent(ABC):
    @staticmethod
    @abstractmethod
    def get_name() -> str:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def from_json(d_json: Dict) -> "AbstractCounter":
        raise NotImplementedError


class GCHeapSummaryEvent(AbstractEvent):
    def __init__(self, gc_id: int, gc_when: str, heap_used: int) -> None:
        self.gc_id = int(gc_id)
        self.gc_when = GCWhen.from_string(gc_when)
        self.heap_used = int(heap_used)

    @staticmethod
    def get_name() -> str:
        return "jdk.GCHeapSummary"

    @staticmethod
    def from_json(d_json: Dict) -> "GCHeapSummaryEvent":
        assert d_json["type"] == GCHeapSummaryEvent.get_name()
        return GCHeapSummaryEvent(
            d_json["values"]["gcId"],
            d_json["values"]["when"],
            d_json["values"]["heapUsed"],
        )


class GarbageCollectionEvent(AbstractEvent):
    def __init__(
        self, gc_id: int, cause: str, total_pause_time: str, longest_pause: str
    ) -> None:
        self.gc_id = int(gc_id)
        self.cause = cause
        self.total_pause_time = isodate.parse_duration(total_pause_time).total_seconds()

    @staticmethod
    def get_name() -> str:
        return "jdk.GarbageCollection"

    @staticmethod
    def from_json(d_json: Dict) -> "GarbageCollectionEvent":
        assert d_json["type"] == GarbageCollectionEvent.get_name()
        return GarbageCollectionEvent(
            d_json["values"]["gcId"],
            d_json["values"]["cause"],
            d_json["values"]["sumOfPauses"],
            d_json["values"]["longestPause"],
        )


# what about duplicate JFR events by different threads?
class PromoteObjectInNewPLABEvent(AbstractEvent):
    def __init__(self, gc_id: int, tenured: bool) -> None:
        self.gc_id = int(gc_id)
        self.tenured = bool(tenured)

    @staticmethod
    def get_name() -> str:
        return "jdk.PromoteObjectInNewPLAB"

    @staticmethod
    def from_json(d_json: Dict) -> "PromoteObjectInNewPLABEvent":
        assert d_json["type"] == PromoteObjectInNewPLABEvent.get_name()
        return PromoteObjectInNewPLABEvent(
            d_json["values"]["gcId"], d_json["values"]["tenured"]
        )


# what about duplicate JFR events by different threads?
class PromoteObjectOutsidePLABEvent(AbstractEvent):
    def __init__(self, gc_id: int, tenured: bool) -> None:
        self.gc_id = int(gc_id)
        self.tenured = bool(tenured)

    @staticmethod
    def get_name() -> str:
        return "jdk.PromoteObjectOutsidePLAB"

    @staticmethod
    def from_json(d_json: Dict) -> "PromoteObjectOutsidePLABEvent":
        assert d_json["type"] == PromoteObjectOutsidePLABEvent.get_name()
        return PromoteObjectOutsidePLABEvent(
            d_json["values"]["gcId"], d_json["values"]["tenured"]
        )


class G1HeapSummaryEvent(AbstractEvent):
    def __init__(
        self,
        gc_id: int,
        gc_when: str,
        eden_used: int,
        survivor_used: int,
        old_used: int,
    ) -> None:
        self.gc_id = int(gc_id)
        self.gc_when = GCWhen.from_string(gc_when)
        self.eden_used = int(eden_used)
        self.survivor_used = int(survivor_used)
        self.old_used = int(old_used)

    @staticmethod
    def get_name() -> str:
        return "jdk.G1HeapSummary"

    @staticmethod
    def from_json(d_json: Dict) -> "G1HeapSummaryEvent":
        assert d_json["type"] == G1HeapSummaryEvent.get_name()
        return G1HeapSummaryEvent(
            d_json["values"]["gcId"],
            d_json["values"]["when"],
            d_json["values"]["edenUsedSize"],
            d_json["values"]["survivorUsedSize"],
            d_json["values"]["oldGenUsedSize"],
        )


class PSHeapSummaryEvent(AbstractEvent):
    def __init__(
        self,
        gc_id: int,
        gc_when: str,
        young_reserved: int,
        young_committed: int,
        old_reserved: int,
        old_committed: int,
    ) -> None:
        self.gc_id = int(gc_id)
        self.gc_when = GCWhen.from_string(gc_when)
        self.young_reserved = int(young_reserved)
        self.young_committed = int(young_committed)
        self.old_reserved = int(old_reserved)
        self.old_committed = int(old_committed)

    @staticmethod
    def get_name() -> str:
        return "jdk.PSHeapSummary"

    @staticmethod
    def from_json(d_json: Dict) -> "PSHeapSummaryEvent":
        assert d_json["type"] == PSHeapSummaryEvent.get_name()
        return PSHeapSummaryEvent(
            d_json["values"]["gcId"],
            d_json["values"]["when"],
            d_json["values"]["youngSpace"]["reservedSize"],
            d_json["values"]["youngSpace"]["committedSize"],
            d_json["values"]["oldSpace"]["reservedSize"],
            d_json["values"]["oldSpace"]["committedSize"],
        )


def split_events_by_gcid(l_events: List) -> List:
    if len(l_events) == 0:
        return dict()
    d_gcid_events = dict()
    for o_event in l_events:
        gcid = o_event.gc_id
        if gcid not in d_gcid_events:
            d_gcid_events[gcid] = list()
        d_gcid_events[gcid].append(o_event)
    min_gcid = min(d_gcid_events.keys())
    max_gcid = max(d_gcid_events.keys())
    for gcid in range(min_gcid, max_gcid + 1):
        if gcid not in d_gcid_events:
            print(f"JFRWARN: Missing GCID {gcid}")
    # assert (max_gcid - min_gcid + 1) == len(d_gcid_events.keys())
    return d_gcid_events


def parse_heap_reclaim_rate(d_gcid_events: Dict) -> List:
    l_reclaim = list()
    l_gcid = list(d_gcid_events.keys())
    l_gcid.sort()
    for gcid in d_gcid_events.keys():
        d_heap_change = {GCWhen.BEFORE_GC: None, GCWhen.AFTER_GC: None}
        for o_event in d_gcid_events[gcid]:
            if isinstance(o_event, GCHeapSummaryEvent):
                assert d_heap_change[o_event.gc_when] is None
                d_heap_change[o_event.gc_when] = o_event.heap_used
        # it is possible gc cycle started just before roi
        # it is possible gc cycle just ended after roi
        if d_heap_change[GCWhen.BEFORE_GC] is None:
            assert gcid == min(l_gcid)
            assert d_heap_change[GCWhen.AFTER_GC] is not None
            continue
        if d_heap_change[GCWhen.AFTER_GC] is None:
            # gen zgc weirdness?
            if gcid != max(l_gcid):
                print(f"JFRWARN: Non-last after GC missing for GCID {gcid}")
            assert d_heap_change[GCWhen.BEFORE_GC] is not None
            continue
        assert d_heap_change[GCWhen.BEFORE_GC] is not None
        assert d_heap_change[GCWhen.AFTER_GC] is not None
        l_reclaim.append(
            op.op_change_percent_inverse(
                d_heap_change[GCWhen.AFTER_GC], d_heap_change[GCWhen.BEFORE_GC]
            )
        )
    return l_reclaim


def get_gc_old_rate(young_size: int, old_size: int) -> float:
    return float(old_size) / (float(old_size) + float(young_size))


def parse_heap_old_usage_rate(d_gcid_events: Dict) -> List:
    l_old_usage = list()
    l_gcid = list(d_gcid_events.keys())
    l_gcid.sort()
    for gcid in d_gcid_events.keys():
        percent_val = None
        for o_event in d_gcid_events[gcid]:
            if (
                isinstance(o_event, G1HeapSummaryEvent)
                and o_event.gc_when == GCWhen.AFTER_GC
            ):
                assert percent_val is None
                percent_val = get_gc_old_rate(
                    o_event.eden_used + o_event.survivor_used, o_event.old_used
                )
            elif (
                isinstance(o_event, PSHeapSummaryEvent)
                and o_event.gc_when == GCWhen.AFTER_GC
            ):
                assert percent_val is None
                percent_val = get_gc_old_rate(
                    o_event.young_committed, o_event.old_committed
                )
        l_old_usage.append(percent_val)
    return l_old_usage


def parse_gc_cycle_promotions(d_gcid_events: Dict) -> List:
    l_promotions = list()
    l_gcid = list(d_gcid_events.keys())
    l_gcid.sort()
    for gcid in d_gcid_events.keys():
        num_promotions = 0
        for o_event in d_gcid_events[gcid]:
            if (
                isinstance(o_event, PromoteObjectInNewPLABEvent)
                and o_event.tenured == True
            ):
                num_promotions += 1
            elif (
                isinstance(o_event, PromoteObjectOutsidePLABEvent)
                and o_event.tenured == True
            ):
                num_promotions += 1
        l_promotions.append(num_promotions)
    return l_promotions


def parse_gc_events(l_events: List) -> [List, List, List]:
    d_gcid_events = split_events_by_gcid(l_events)
    return (
        parse_heap_reclaim_rate(d_gcid_events),
        parse_heap_old_usage_rate(d_gcid_events),
        parse_gc_cycle_promotions(d_gcid_events),
    )
