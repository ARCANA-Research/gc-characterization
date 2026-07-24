#!/bin/bash

set -e

BASE_DIR=$(pwd)
if [[ $# -eq 1 ]]; then
  BASE_DIR=$1
fi

VENV_DIR=$BASE_DIR/.venv
DEPS_DIR=$BASE_DIR/deps
PATCHES_DIR=$BASE_DIR/patches
RUNNING_NG_DIR=$DEPS_DIR/running-ng
DACAPO_DIR=$DEPS_DIR/dacapo-23.11-MR2-chopin
JDK21_BOOT_DIR=$DEPS_DIR/jdk-21.0.2
JDK21_COUNTER_DIR=$DEPS_DIR/jdk21u-counter
JDK21_SIMULATOR_DIR=$DEPS_DIR/jdk21u-simulator
GEM5_DIR=$DEPS_DIR/gem5
RAMULATOR2_DIR=$GEM5_DIR/ext/ramulator2/ramulator2

if [ ! -d "$DEPS_DIR" ]; then
  mkdir -p $DEPS_DIR
fi


if [ ! -d "$VENV_DIR" ]; then
  echo "Setup virtualenv"
  python3 -m venv $VENV_DIR
  source $VENV_DIR/bin/activate
  python -m pip install -r $BASE_DIR/requirements.txt
  deactivate
else
  echo "Skip virtualenv"
fi

if [ ! -d "$RUNNING_NG_DIR" ]; then
  echo "Setup running-ng"
  git clone --revision=53b4be62b48e00fceab6308cdc8c4d4cf7e10000 https://github.com/anupli/running-ng.git $RUNNING_NG_DIR
  git -C $RUNNING_NG_DIR apply $PATCHES_DIR/running-ng.patch
  source $VENV_DIR/bin/activate
  pip install $RUNNING_NG_DIR
  deactivate
else
  echo "Skip running-ng"
fi

if [ ! -d "$DACAPO_DIR" ]; then
  echo "Setup dacapo"
  wget -P $DEPS_DIR https://download.dacapobench.org/chopin/dacapo-23.11-MR2-chopin.zip
  unzip $DEPS_DIR/dacapo-23.11-MR2-chopin.zip -d $DEPS_DIR
else
  echo "Skip dacapo"
fi

if [ ! -d "$JDK21_BOOT_DIR" ]; then
  echo "Setup boot JDK21"
  wget -P $DEPS_DIR https://download.java.net/java/GA/jdk21.0.2/f2283984656d49d69e91c558476027ac/13/GPL/openjdk-21.0.2_linux-x64_bin.tar.gz
  tar xvf $DEPS_DIR/openjdk-21.0.2_linux-x64_bin.tar.gz -C $DEPS_DIR
else
  echo "Skip boot JDK21"
fi

if [ ! -d "$JDK21_COUNTER_DIR" ]; then
  echo "Setup counter JDK21"
  git clone --revision=7069f193f1f8c61869fc68a36c17f3a9a7b7b2a0 https://github.com/openjdk/jdk21u.git $JDK21_COUNTER_DIR
  git -C $JDK21_COUNTER_DIR apply $PATCHES_DIR/jdk21u-counter.patch
  env --chdir=$JDK21_COUNTER_DIR bash configure --with-jvm-variants=server \
    --with-boot-jdk=$JDK21_BOOT_DIR \
    --enable-jvm-feature-parallelgc \
    --enable-jvm-feature-serialgc \
    --enable-jvm-feature-shenandoahgc \
    --enable-jvm-feature-zgc \
    --enable-jvm-feature-g1gc \
    --enable-jvm-feature-epsilongc \
    --enable-jvm-feature-jvmti \
    --enable-counter-events \
    --enable-counter-finer-events
  make -C $JDK21_COUNTER_DIR images CONF=linux-x86_64-server-release
else
  echo "Skip counter JDK21"
fi

if [ ! -d "$JDK21_SIMULATOR_DIR" ]; then
  echo "Setup simulator JDK21"
  git clone --revision=7069f193f1f8c61869fc68a36c17f3a9a7b7b2a0 https://github.com/openjdk/jdk21u.git $JDK21_SIMULATOR_DIR
  git -C $JDK21_SIMULATOR_DIR apply $PATCHES_DIR/jdk21u-simulator.patch
  env --chdir=$JDK21_SIMULATOR_DIR bash configure --with-jvm-variants=client \
    --with-boot-jdk=$JDK21_BOOT_DIR \
    --enable-jvm-feature-parallelgc \
    --enable-jvm-feature-serialgc \
    --enable-jvm-feature-shenandoahgc \
    --enable-jvm-feature-zgc \
    --enable-jvm-feature-g1gc \
    --enable-jvm-feature-epsilongc \
    --enable-jvm-feature-jvmti \
    --with-extra-cxxflags="-I$BASE_DIR/src/simulator/include"
  make -C $JDK21_SIMULATOR_DIR images CONF=linux-x86_64-client-release
else
  echo "Skip simulator JDK21"
fi

if [ ! -d "$GEM5_DIR" ]; then
  echo "Setup gem5"
  git clone --revision=c9625ce9cc5b5a90a38327de5ac0e1870974af5e https://github.com/gem5/gem5.git $GEM5_DIR
  git -C $GEM5_DIR apply $PATCHES_DIR/gem5.patch
  git clone --revision=e62c84a6f0e06566ba6e182d308434b4532068a5 https://github.com/CMU-SAFARI/ramulator2 $RAMULATOR2_DIR
  git -C $RAMULATOR2_DIR apply --ignore-space-change --ignore-whitespace $PATCHES_DIR/ramulator2.patch
  mkdir $RAMULATOR2_DIR/build
  cd $RAMULATOR2_DIR/build
  cmake ..
  make -j$(nproc)
  cd $GEM5_DIR
  scons build/X86/gem5.fast -j$(nproc) --ignore-style
  cd $BASE_DIR
else
  echo "Skip gem5"
fi
