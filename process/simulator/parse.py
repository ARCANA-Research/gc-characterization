import argparse
import os
import sys

sys.path.append(os.path.abspath("support"))
from common import parallelize, progress, utils
from common.simulation import simulation_utils


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--outdir", required=True, nargs=1)
    args = parser.parse_args()
    p_curr = utils.get_currdir()
    p_outdir = args.outdir[0]
    y_check = utils.parse_yaml(f"{p_outdir}/check.yaml")
    utils.wipe_log(f"{p_outdir}/run.log")
    l_args = list()
    for p_process in y_check["PROCESS"] + y_check["SAMPLE"]:
        l_args.append(
            {
                "outdir": p_outdir,
                "execution": p_process,
            }
        )
    progress_bar = progress.start(f"Parsing Executions", len(l_args) * 2)
    for arg in l_args:
        progress.advance(progress_bar)
        cmd = f"python {p_curr}/process/simulator/benchmark/parse.py --outdir {arg['outdir']} --execution {arg['execution']}"
        parallelize.execute_subprocess(cmd, f"{p_outdir}/run.log")
        progress.advance(progress_bar)
    progress.end(progress_bar)
    progress_bar = progress.start(f"Combine Parsing", 1)
    simulation_utils.combine_parse(
        p_outdir, y_check["PROCESS"] + y_check["SAMPLE"], "simulator"
    )
    progress.advance(progress_bar)
    progress.end(progress_bar)


if __name__ == "__main__":
    main()
