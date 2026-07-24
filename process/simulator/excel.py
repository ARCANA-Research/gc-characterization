import argparse
import os
import sys

sys.path.append(os.path.abspath("support"))
from common import excel, progress, utils


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--outdir", required=True, nargs=1)
    parser.add_argument("--suite", required=True, nargs=1)
    args = parser.parse_args()
    p_outdir = args.outdir[0]
    suite_name = args.suite[0]
    p_curr = utils.get_currdir()
    p_excel = f"{p_outdir}/excel"
    utils.create_folder_if_not_exist_and_archive_existing_files(p_excel)
    p_eventmap = f"{p_curr}/support/eventmap.yaml"
    progress_bar = progress.start(f"Reading Analysis", 1)
    l_analysis = utils.parse_json(f"{p_outdir}/analysis.json")
    l_analysis_per_phase = utils.parse_json(f"{p_outdir}/analysis_perphase.json")
    d_analysis_split = excel.split_analysis(l_analysis)
    d_analysis_split_pp = excel.split_analysis(l_analysis_per_phase)
    progress.advance(progress_bar)
    progress.end(progress_bar)
    assert set(d_analysis_split.keys()) == set(d_analysis_split_pp.keys())
    progress_bar = progress.start(f"Generating Excel", len(d_analysis_split.keys()))
    for k in d_analysis_split.keys():
        excel_prepend = None
        if k != "base":
            excel_prepend = k
        excel.save_excel(
            d_analysis_split[k],
            p_excel,
            p_eventmap,
            excel.per_benchmark,
            suite_name,
            excel_prepend,
        )
        excel.save_excel(
            d_analysis_split[k],
            p_excel,
            p_eventmap,
            excel.per_gc,
            suite_name,
            excel_prepend,
        )
        excel.save_excel(
            d_analysis_split[k],
            p_excel,
            p_eventmap,
            excel.by_gc,
            suite_name,
            excel_prepend,
        )
        excel.save_excel(
            d_analysis_split[k],
            p_excel,
            p_eventmap,
            excel.heatmap,
            suite_name,
            excel_prepend,
        )
        # excel.save_excel_per_analysis(
        #     d_analysis_split_pp[k], p_excel, p_eventmap, excel.per_phase_combined, suite_name, excel_prepend
        # )
        # excel.save_excel_per_analysis(
        #     d_analysis_split_pp[k],
        #     p_excel,
        #     p_eventmap,
        #     excel.per_phase_total,
        #     suite_name,
        #     excel_prepend,
        # )
        # excel.save_excel_per_analysis(
        #     d_analysis_split_pp[k],
        #     p_excel,
        #     p_eventmap,
        #     excel.per_phase_nongc,
        #     suite_name,
        #     excel_prepend,
        # )
        # excel.save_excel_per_analysis(
        #     d_analysis_split_pp[k],
        #     p_excel,
        #     p_eventmap,
        #     excel.per_phase_gcstw,
        #     suite_name,
        #     excel_prepend,
        # )


if __name__ == "__main__":
    main()
