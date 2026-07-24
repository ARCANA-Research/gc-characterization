import argparse
import os
import sys

sys.path.append(os.path.abspath("support"))
from common import excel, progress, utils


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--outdir", required=True, nargs=1)
    parser.add_argument("--suite", required=False, nargs=1)
    args = parser.parse_args()
    p_outdir = args.outdir[0]
    p_artifact = utils.get_currdir()
    p_excel = f"{p_outdir}/excel"
    utils.create_folder_if_not_exist_and_archive_existing_files(p_excel)
    p_eventmap = f"{p_outdir}/eventmap.yaml"
    if os.path.exists(p_eventmap) == False:
        p_eventmap = f"{p_artifact}/support/eventmap.yaml"
    progress_bar = progress.start(f"Reading Analysis", 1)
    l_analysis = utils.parse_json(f"{p_outdir}/analysis.json")
    progress.advance(progress_bar)
    progress.end(progress_bar)
    if args.suite is None:
        suite_name = utils.parse_yaml(f"{p_outdir}/config.yaml")["suite"]
    else:
        suite_name = args.suite[0]
    excel.save_excel(l_analysis, p_excel, p_eventmap, excel.per_benchmark, suite_name)
    excel.save_excel(l_analysis, p_excel, p_eventmap, excel.per_gc, suite_name)
    excel.save_excel(l_analysis, p_excel, p_eventmap, excel.by_gc, suite_name)
    excel.save_excel(l_analysis, p_excel, p_eventmap, excel.heatmap, suite_name)


if __name__ == "__main__":
    main()
