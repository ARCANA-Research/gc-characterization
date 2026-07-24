import argparse
import os
import sys
import yaml

from typing import Dict, List

sys.path.append(os.path.abspath("support"))
from common import analysis, utils, jvm
from common.simulation import simulation_utils


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--outdir", required=True, nargs=1)
    args = parser.parse_args()
    p_outdir = args.outdir[0]
    p_curr = utils.get_currdir()
    p_analysis = f"{p_curr}/support/simulator/stats/analysis.yaml"
    p_counters = f"{p_curr}/support/simulator/stats/counters.yaml"
    l_counters, l_per_phase_counters = simulation_utils.get_counters(p_counters)
    l_analysis = analysis.get_valid_analysis(
        p_analysis, l_counters, l_per_phase_counters, jvm.EXPECTED_SIMULATION_ITERATIONS
    )
    l_results = utils.parse_json(f"{p_outdir}/results.json")
    l_process, l_sampled = analysis.split_process_and_sampled_data(l_results)
    l_process_combined, l_process_per_phase = analysis.generate_analysis(
        l_process, l_analysis, False
    )
    l_process_combined_pp, l_process_per_phase_pp = analysis.generate_analysis(
        l_process, l_analysis, True
    )
    l_sampled_combined, l_sampled_per_phase = analysis.generate_analysis(
        l_sampled, l_analysis, False, "sa-"
    )
    l_sampled_combined_pp, l_sampled_per_phase_pp = analysis.generate_analysis(
        l_sampled, l_analysis, True, "sa-"
    )
    l_all_combined, l_all_per_phase = analysis.generate_analysis(
        l_results, l_analysis, False, "all-"
    )
    l_all_combined_pp, l_all_per_phase_pp = analysis.generate_analysis(
        l_results, l_analysis, True, "all-"
    )
    l_data_combined = (
        l_process_combined
        + l_process_combined_pp
        + l_sampled_combined
        + l_sampled_combined_pp
        + l_all_combined
        + l_all_combined_pp
    )
    l_data_per_phase = (
        l_process_per_phase
        + l_process_per_phase_pp
        + l_sampled_per_phase
        + l_sampled_per_phase_pp
        + l_all_per_phase
        + l_all_per_phase_pp
    )
    utils.save_json(l_data_combined, f"{p_outdir}/analysis.json")
    utils.save_json(l_data_per_phase, f"{p_outdir}/analysis_perphase.json")


if __name__ == "__main__":
    main()
