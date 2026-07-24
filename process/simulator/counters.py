import argparse
import os
import sys

sys.path.append(os.path.abspath("support"))
from common import utils, parallelize, progress


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--outdir", required=True, nargs=1)
    args = parser.parse_args()
    p_curr = utils.get_currdir()
    p_outdir = args.outdir[0]
    y_check = utils.parse_yaml(f"{p_outdir}/check.yaml")
    utils.wipe_log(f"{p_outdir}/run.log")
    l_args = list()
    progress_bar = progress.start(f"Parsing Counters", len(y_check["PROCESS"]) * 2)
    for p_process in y_check["PROCESS"]:
        progress.advance(progress_bar)
        cmd = f"python {p_curr}/process/simulator/benchmark/counters.py --outdir {p_outdir} --execution {p_process}"
        parallelize.execute_subprocess(cmd, f"{p_outdir}/run.log")
        progress.advance(progress_bar)
    progress.end(progress_bar)
    progress_bar = progress.start(f"Sampling Counters", len(y_check["SAMPLE"]) * 2)
    for p_process in y_check["SAMPLE"]:
        progress.advance(progress_bar)
        cmd = f"python {p_curr}/process/simulator/benchmark/counters.py --outdir {p_outdir} --execution {p_process} --sampled"
        parallelize.execute_subprocess(cmd, f"{p_outdir}/run.log")
        progress.advance(progress_bar)
    progress.end(progress_bar)


if __name__ == "__main__":
    main()
