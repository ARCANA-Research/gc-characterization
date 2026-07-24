#!/bin/bash

set -e

CURRDIR=$(pwd)
RUNDIR=$CURRDIR/run/simulator
PROCESSDIR=$CURRDIR/process/simulator

source .venv/bin/activate

CMD_OUT_PATH=$(python $RUNDIR/setup.py)
echo "INFO: working output directory: $CMD_OUT_PATH"

python $RUNDIR/cmd.py --outdir $CMD_OUT_PATH &>> $CMD_OUT_PATH/run.log

START_TIME="$(date +%Y.%m.%d_%H:%M:%S)"
echo "START TIME: $START_TIME" &>> $CMD_OUT_PATH/run.log

python $RUNDIR/execute.py --outdir $CMD_OUT_PATH

END_TIME="$(date +%Y.%m.%d_%H:%M:%S)"
echo "END TIME: $END_TIME" &>> $CMD_OUT_PATH/run.log

python $PROCESSDIR/check.py --outdir $CMD_OUT_PATH &>> $CMD_OUT_PATH/run.log
python $PROCESSDIR/parse.py --outdir $CMD_OUT_PATH &>> $CMD_OUT_PATH/run.log
python $PROCESSDIR/analysis.py --outdir $CMD_OUT_PATH &>> $CMD_OUT_PATH/run.log
python $PROCESSDIR/excel.py --outdir $CMD_OUT_PATH --suite dacapo &>> $CMD_OUT_PATH/run.log

deactivate
