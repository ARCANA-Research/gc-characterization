import argparse
import os
import sys

sys.path.append(os.path.abspath("support"))
from common import parallelize, progress, utils
from common.simulation import check_utils, simulation_utils


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--skipcheck", required=False, action="store_true")
    args = parser.parse_args()
    p_outdir = args.outdir
    p_curr = utils.get_currdir()
    l_args, l_expected_executions = check_utils.generate_args(p_outdir)
    if args.skipcheck == False:
        utils.wipe_log(f"{p_outdir}/run.log")
        progress_bar = progress.start(f"Checking Executions", len(l_args) * 2)
        for arg in l_args:
            progress.advance(progress_bar)
            cmd = f"python {p_curr}/process/simulator/benchmark/check.py --outdir {arg['outdir']} --execution {arg['execution']}"
            parallelize.execute_subprocess(cmd, f"{p_outdir}/run.log")
            progress.advance(progress_bar)
        progress.end(progress_bar)
    progress_bar = progress.start("Combining Check Files", 1)
    check_utils.process_outdir(
        l_expected_executions,
        p_outdir,
        f"{p_curr}/support/simulator/statusmap.yaml",
        "simulator",
        simulation_utils.split_benchmark_path,
    )
    progress.advance(progress_bar)
    progress.end(progress_bar)


if __name__ == "__main__":
    main()
