# GC Characterization Paper

> [!NOTE]
> This repository contains artifacts for our OOPSLA 2026 paper that analyzed the memory system overheads for garbage collection algorithms in OpenJDK 21. Please cite that paper if you use our code in your research.

Garbage collection (GC) is an integral part of the Java Virtual Machine but it is not trivial to analyze the overheads of modern GC implementations. This repository contains a set of tools that can be used to characterize GC implementations in OpenJDK 21.

Our paper develops a thread and pause-based GC overhead estimation toolkit that uses performance counters and fine-grained event tracking mechanism in [gem5](https://github.com/gem5/gem5) simulation to measure GC's overheads in the memory system.

We use workloads from the DaCapo Benchmark Suite for analysis in our paper -> https://download.dacapobench.org/chopin/dacapo-23.11-MR2-chopin.zip

## System Requirements

We tested our toolkit on Ubuntu 20.04 and Ubuntu 24.04 (counter only). The instructions and code, however, *should* work on any modern x86 Debian-based operating system. 

> [!Warning]
> The JDK used in gem5 should be compiled on a GLIBC version compatible with Ubuntu 22.04, the operating system simulated in gem5. We recommend using Ubuntu 20.04 to reproduce our results.

We compile custom binaries for OpenJDK 21 and gem5 using patches in `patches/` and download the benchmark suite when building the source code. This is a resource intensive task that downloads over 6GB of data and compiles multiple very large code bases. This build process executes in under 10 minutes on our system.

> [!Tip]
> Using custom OpenJDK 21 and gem5 code is not necessary to use our tool but is necessay to reproduce the paper's claims. If you choose to use your own binaries, please change the paths to these dependencies in `CMakeLists.txt`.

## Dependencies


We build OpenJDK from scratch, which expects the following system packages to be availabile:

```
apt-get install libasound2-dev libcups2-dev libfontconfig1-dev libx11-dev libxext-dev libxrender-dev libxrandr-dev libxtst-dev libxt-dev
```

We also compile a modified version of gem5, which expects the following system packages to be installed:

```
apt-get install build-essential git gdb m4 scons build-essential cmake zlib1g zlib1g-dev libprotobuf-dev protobuf-compiler libprotoc-dev libgoogle-perftools-dev python3-dev doxygen libboost-all-dev libhdf5-serial-dev python3-pydot libpng-dev libelf-dev pkg-config pip python3-venv black libcapstone-dev
```

The build process for *all* dependencies and binaries is automated via cmake. The process requires creating a new `build` directory where the binaries are stored.

```
./setup.sh
mdkir build
cd build
cmake ..
make -j$(nproc)
./setup-image.sh
```

> [!WARNING]
> Some dependencies, such as DaCapo Benchmark Suite, are over 6GB in sizes, and the build process for some--especially OpenJDK and gem5--is compute and memory intensive. These are downloaded and compiled by `setup.sh` automatically.

Dependencies are installed via `setup.sh` in the `deps` directory, and gem5 images are built with `setup-image.sh`. If you choose to download, build, and install dependencies, please refer to these files for build commands.

We support the following compiler flags passed to cmake using `cmake -D<FLAG>=ON ..`:

| Flag | Default | Description |
| - | - | - |
| `DEBUG_LOG` | ❌ | Enable debug logging |
| `USE_COUNTER_GC_EVENTS` | ✅ | Use custom GC events |

### Performance Counter Binaries

A significant part of our work usees performance counters to measure GC overhead. The following binaries are compiled by cmake and attach as Java Agents using JNI.

| Binary | Description |
| - | - |
| Agent | Measures time, and GC events only |
| Concurrent | Measures concurrent GC performance counters  (our primary source of data)|

The following libraries disable prefetching support. We change the L2 prefetching MSR for Intel's Xeon Cascade Lake platform. Note that it is possible that the prefetching MSR is different for your machine.

> [!Caution]
> The binaries that disable prefetching change CPU behavior by writing to specific [MSRs](https://en.wikipedia.org/wiki/Model-specific_register).

| Binary | Description |
| - | - |
| No Prefetcher | Disable L2 prefetching for GC cores |
| No Prefetcher Concurrent | Disable prefetching for GC cores during concurrent execution |
| No Prefetcher STW | Disable prefetching for *all* cores during pauses, and GC cores are always disabled |

We also compile a `callback` shared library that uses DaCapo Benchmark's Harness system to trigger region-of-interest events from workloads.

### Simulation Framework

We use gem5's m5 magic instructions to trigger Java events and track GC threads. The only binaries compiled are for DaCapo Benchmark's Harness system and the `.class` file that is executed by Java. 

> [!Tip]
> `simulator.hpp` in `src/simualtor/include` is the source of truth for magic instructions for our JDK implementation. If you want to switch to address based triggers, please refer to gem5's documentation -> https://github.com/gem5/gem5/tree/stable/util/m5

We enable access to DaCapo Benchmark Suite in gem5 using an external image that is loaded as an external disk to Ubuntu.

#### Change Ubuntu image
This is an optional step that we perform to simplify simulation config. We change `gem5_init.sh` to mount benchmark image on boot during `setup.sh` execution.

## Execute Program

`config.yaml` specifies what workloads are executed and the system state for their execution. 

> [!Caution]
> Please specify an output directory in `config.yaml` before executing workloads. Execution will fail without a valid path.

### GC Thread Isolation

We isolate benchmark execution from other applications to improve measurement accuracy. However, we do not use `isolcpus` as it disables the load balancer, leading to inaccurate execution.

We split our system's CPUs into two groups where one of the groups executes the benchmarks, and the other executes monitoring tools and other software. These groups, by default, are the two sockets on the machine, and are shown below:

```
System CPU(s): 0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46
Benchmark CPU(s): 1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,31,33,35,37,39,41,43,45,47
```

> [!WARNING]
> Please choose the appropriate CPU(s) and NUMA node(s) for threads launched by OpenJDK for your system that minimizes inference by other applications.

These CPUs can be isolated (i.e., not have any tasks scheduled by the kernel) using [cgroups v2](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html).

> Ubuntu documentation -> https://documentation.ubuntu.com/real-time/latest/how-to/isolate-workload-cpusets/

Our toolkit requires cgroups v2, which can be enabled by adding `systemd.unified_cgroup_hierarchy=1` to to `GRUB_CMDLINE_LINUX` in `/etc/default/grub`. The bootloader should be updated after changes to the command line arguments.

```
sudo update-grub
```

First, move all system and user processes to one part of the CPU:

```
systemctl set-property --runtime init.scope AllowedCPUs=0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46
systemctl set-property --runtime system.slice AllowedCPUs=0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46
systemctl set-property --runtime user.slice AllowedCPUs=0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46
```

Then, create a new slice to execute benchmarks:

```
systemctl set-property --runtime counter.slice AllowedCPUs=1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,31,33,35,37,39,41,43,45,47
```

Applications can run on the slice using `systemd-run`:

```
systemd-run --scope --property=Slice=counter.slice
```

> [!Caution]
> Enabling priviledged access without `sudo` is not recommended and should not be implemented unless needed.

`systemd-run` requires root access to run programs, but that can--ideally should not--be prevented by adding a custom `polkit` rule.

We use a `plka` file in our analysis:

```
cd /etc/polkit-1/localauthority/50-local.d
touch 55-counter.pkla
```

The `pkla` file, specified below, allows `arcana` to execute `systemd-run` without `sudo`.

```
[Allow arcana to use system-run without sudo]
Identity=unix-user:arcana
Action=org.freedesktop.systemd1.manage-units
ResultAny=yes
ResultInactive=yes
ResultActive=yes
```

`polkit` will reload when the file is saved.

### Change System Settings

`/proc/sys/kernel/perf_event_paranoid` needs to be set to -1 for the code to work correctly, enabling unpriviledged access to performance counters:

```
echo -1 | sudo tee /proc/sys/kernel/perf_event_paranoid
```

Platform specific counters can be found by running the `showevtinfo` example in the `libpfm4` library (compiled automatically in the `ext` directory). 

### Disable SMT

It *might* help to disable SMT to compare counters with gem5 simulation (as the simulator does not implement SMT):
```
echo off | sudo tee /sys/devices/system/cpu/smt/control
```
SMT can be re-enabled with the following command:
```
echo on | sudo tee /sys/devices/system/cpu/smt/control
```

## Reproducibe Experiments

The first step for reproducing the results of our work is to estimate the minimum heap for all GC implementations using [`minheap`](https://anupli.github.io/running-ng/commands/minheap.html) command in `running-ng`. We follow the DaCapo Benchmark Suite's methodology, specified on their code repository -> https://github.com/dacapobench/dacapobench/tree/main/tools/analysis/minheap.

> [!Note]
> The minimum heaps for workloads used in our analysis are specified in the supplementary appendix of the paper.

We execute "default" and "large" workload size on performance counters and "default" in simulation in our paper.

`run-counter.sh` measures GC overhead using performance counters. `config.yaml` defines which counters are read using a counters file. We verify how workloads executing using `verify` binary that checks if JDK threads executed on the correct CPUs. 

`run-simulator.sh` executes workloads in gem5. We execute workloads just once in the simulator.

### Output Format

The final output format is in terms of .xlsx files (Microsoft Excel sheets) saved to the path specified on script execution, under the "excel" folder. However, it is possible that some benchmarks fail to execute correctly. `check.yaml`--and `check.ansi`--show which benchmarks passed and failed verification check, and why. If no benchmarks execute correctly, no Microsoft Excel output is generated. 