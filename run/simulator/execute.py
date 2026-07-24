import argparse
import os
import sys

sys.path.append(os.path.abspath("support"))
from common import execute, utils


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--outdir", required=True, nargs=1)
    args = parser.parse_args()
    p_output = args.outdir[0]
    config = utils.parse_yaml(f"{p_output}/config.yaml")
    parallel_executions = config["simulator"]["parallel_executions"]
    execute.execute_benchmarks(p_output, parallel_executions)


if __name__ == "__main__":
    main()
