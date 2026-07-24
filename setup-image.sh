#!/bin/bash

set -e

BASE_DIR=$(pwd)
VENV_DIR=$BASE_DIR/.venv
DEPS_DIR=$BASE_DIR/deps
PATCHES_DIR=$BASE_DIR/patches
GEM5_DIR=$DEPS_DIR/gem5
JDK21_SIMULATOR_DIR=$DEPS_DIR/jdk21u-simulator
IMG_MNT=$DEPS_DIR/image_mnt
UBUNTU_IMG=$DEPS_DIR/x86-ubuntu-22.04
BENCHMARK_IMG=$DEPS_DIR/benchmark.img

if [ ! -d "$IMG_MNT" ]; then
  echo "Setup image mount"
  mkdir -p $IMG_MNT
else
  echo "Skip image mount"
fi

if [ ! -f "$UBUNTU_IMG" ]; then
  echo "Setup ubuntu image"
  wget -P $DEPS_DIR https://dist.gem5.org/dist/develop/images/x86/x86-ubuntu-22-04.gz
  gzip -dc $DEPS_DIR/x86-ubuntu-22-04.gz > $UBUNTU_IMG
  sudo mount -o loop,offset=2097152 $UBUNTU_IMG $IMG_MNT
  sudo cp $PATCHES_DIR/gem5_init.sh $IMG_MNT/sbin/gem5_init.sh
  sudo mkdir $IMG_MNT/benchmark
  sudo umount $IMG_MNT
else
  echo "Skip ubuntu image"
fi

if [ ! -f "$BENCHMARK_IMG" ]; then
  echo "Setup benchmark image"
  $GEM5_DIR/util/gem5img.py init $BENCHMARK_IMG 8192
  dd if=/dev/zero bs=1G count=12 >> $BENCHMARK_IMG
  fdisk -l $BENCHMARK_IMG
  sudo parted $BENCHMARK_IMG resizepart 1 100%
  fdisk -l $BENCHMARK_IMG
  sudo mount -o loop,offset=1048576 $BENCHMARK_IMG $IMG_MNT
  sudo resize2fs $(losetup -j $BENCHMARK_IMG| cut -d: -f1)
  sudo cp -r $BASE_DIR/support/jfr $IMG_MNT
  sudo cp -R $BASE_DIR/build/src/simulator $IMG_MNT/build
  sudo cp $DEPS_DIR/dacapo-23.11-MR2-chopin.jar $IMG_MNT
  sudo cp -r $DEPS_DIR/dacapo-23.11-MR2-chopin $IMG_MNT
  sudo cp -r $JDK21_SIMULATOR_DIR/build/linux-x86_64-client-release/images/jdk $IMG_MNT
  sudo umount $IMG_MNT
else
  echo "Skip benchmark image"
fi
