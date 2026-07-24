import argparse
import os
import sys
import yaml

from typing import Dict, List

sys.path.append(os.path.abspath("support"))
from common import analysis, utils


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--outdir", required=True, nargs=1)
    args = parser.parse_args()
    p_outdir = args.outdir[0]
    p_artifact = utils.get_currdir()
    p_analysis = f"{p_artifact}/support/counter/analysis.yaml"
    y_results = utils.parse_json(f"{p_outdir}/results.json")
    (
        l_combined_counters,
        l_per_phase_counters,
        expected_iterations,
    ) = analysis.get_combined_and_per_phase_counters(y_results)
    l_analysis = analysis.get_valid_analysis(
        p_analysis, l_combined_counters, l_per_phase_counters, expected_iterations
    )
    l_data_combined, l_data_per_phase = analysis.generate_analysis(
        y_results, l_analysis, False
    )
    l_data_combined_pp, l_data_per_phase_pp = analysis.generate_analysis(
        y_results, l_analysis, True
    )
    l_data_combined += l_data_combined_pp
    l_data_per_phase += l_data_per_phase_pp
    utils.save_json(l_data_combined, f"{p_outdir}/analysis.json")
    utils.save_json(l_data_per_phase, f"{p_outdir}/analysis_perphase.json")


if __name__ == "__main__":
    main()
