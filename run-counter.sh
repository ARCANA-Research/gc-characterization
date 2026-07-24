#!/bin/bash

BASEDIR=$(pwd)
RUNDIR=$BASEDIR/run/counter
PROCESSDIR=$BASEDIR/process/counter

RUNNING_DIR=$BASEDIR/deps/running-ng

source .venv/bin/activate

CMD_OUT_PATH=$(python $RUNDIR/config.py)
echo "INFO: working output directory: $CMD_OUT_PATH"

START_TIME="$(date +%Y.%m.%d_%H:%M:%S)"
echo "START TIME: $START_TIME" &>> $CMD_OUT_PATH/run.log

python $RUNDIR/run.py --outdir $CMD_OUT_PATH

END_TIME="$(date +%Y.%m.%d_%H:%M:%S)"
echo "END TIME: $END_TIME" &>> $CMD_OUT_PATH/run.log

python $PROCESSDIR/check.py --outdir $CMD_OUT_PATH &>> $CMD_OUT_PATH/run.log
python $PROCESSDIR/parse.py --outdir $CMD_OUT_PATH &>> $CMD_OUT_PATH/run.log
python $PROCESSDIR/analysis.py --outdir $CMD_OUT_PATH &>> $CMD_OUT_PATH/run.log
python $PROCESSDIR/excel.py --outdir $CMD_OUT_PATH &>> $CMD_OUT_PATH/run.log

deactivate
