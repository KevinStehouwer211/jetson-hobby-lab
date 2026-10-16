# Working setup and validation record

Hardware validation took place on 2026-10-15/16 using the same native Python
implementation now copied into this folder. Full raw logs remain in
`~/yahboom-dofbot/diagnostics/`; they are not replayed or published by setup.

| Area | Evidence |
|---|---|
| Hardware | Jetson Orin Nano Super, L4T R36.4.7, DOFBOT bus 7/address 0x15, reported controller version 0.21 |
| Queries | All six pings 0xDA, valid joint positions |
| Servo 1, repeated 15° targets | 114/99/114 requested; 113/99/113 feedback, all passed |
| Servo 1, 15° outward/return | 128/113 requested; 127/113 feedback, both passed |
| Servos 2–6, 10° outward/return | All ten legs passed within 1° of target; user confirmed physical movement |
| Servo 1, fastest 45° outward/return | Duration 0; 158/113 requested; 157/113 feedback, both passed |
| Physical observation | User confirmed servo-1 movement and the five other joints' sweeps; subsequently described the fast test as “perfect” |
| Environment | Local launcher imports Arm_Lib, rclpy, PyTorch, OpenCV and NumPy; no global installs or replacements |

## Why the library has a recovery delay

Original valid writes often produced no movement despite successful I²C calls.
Kernel tracing showed the correct five-byte position packet, successful driver
completion, and no competing controller-address traffic in the captured run.
A raw-I²C alternative had a single success but did not repeat; that candidate
transport change was reverted.

The vendor supplies a helper requesting 100 kHz. That setup step was initially
missed because its old sysfs interface is absent on the new kernel. A boot-time
overlay established the requested configuration. Changing the clock alone did
not fix movement. At 100 kHz, an additional 100 ms gap after feedback reads
produced a physically confirmed movement. An early repeatability test then
stopped on a missing response from an immediate back-to-back read.

The recovery gap was moved into `Arm_serial_servo_read()` and
`Arm_serial_servo_read_any()` so the caller's next read or write inherits it.
Subsequent bounded tests passed for all six joints through the ordinary API.
The two read methods still use the vendor request/register and byte conversion.
Only the standard read API was exercised live; `read_any` shares the candidate
recovery behavior but has not been independently validated on hardware.

A 100 ms delay is a conservative tested value, not a measured minimum or a
firmware specification. The pause adds read latency; it does not serialize
other instances/processes/threads. Use a single owner for the bus/controller.
No motion completion acknowledgement is returned by the write API; position
feedback and physical observation were used to judge the tests.

## Deliberate limits

The basic `set_dofbot.py` pose script was subsequently edited to read after each
write. An immediate feedback request returned raw zero for servo 1. The script
now waits for the requested movement duration plus one second before querying,
and stops before subsequent joints if feedback is missing. That revision was
checked with fake hardware; its current editable multi-joint pose has not been
physically validated by the agent. The write-only/read-only script distinction
and the setup/rebuild work do not imply that every user-selected pose is safe.

These results do not establish long-duration reliability, all mechanical poses,
concurrent control, high-rate write bursts, simultaneous six-joint packets, or
400 kHz operation with the new recovery delay. No firmware, calibration offsets,
IDs, or torque settings were changed during the successful tests. The current
manual's full ROS/vision application was not started or validated.

The runtime dependencies already present include PyTorch
`2.5.0a0+872d972e41.nv24.08`, torchvision `0.20.0a0+afc54f7`, OpenCV `4.10.0`,
NumPy `1.23.5`, native smbus `1.1.post2`, and smbus2 `0.5.0`. The local venv
reuses those packages rather than installing generic replacements.

Offline tests cover packet mappings for every joint, error reporting, recovery
ordering against a busy-controller model, authorization gates, joint limits,
fixed endpoints without accumulated feedback rounding, and stop-on-first-failure.
Run them with the command in the main README; they do not open real hardware.

## Repository packaging checks (2026-10-16)

- All 23 hardware-free diagnostic tests passed from the new folder.
- Python/shell syntax, vendor manifest checksums, notebook cleanup, credential
  placeholders, and Git asset exclusions were checked.
- The new launcher imported the repository's Arm_Lib together with rclpy,
  PyTorch, OpenCV, and NumPy; no controller instance/model/camera was started.
- An actual project-local Jupyter kernel imported the new library and ROS.
- A temporary localhost JupyterLab login page responded using the existing
  shared JupyterLab web assets. The verification kernel/server were shut down.
- Asset-only recovery was checked against actual Git ignore rules in a tiny
  temporary repository: source edits and existing assets were preserved.
- No vendor notebook was executed and no hardware commands were sent during
  packaging. Git changes were left local, uncommitted and unpushed.

## Rebuild and cleanup audit (2026-10-16)

- Added a complete [rebuild checklist](REBUILD.md), board-specific overlay
  compile/install/rollback steps, minimal pinned servo dependencies, a reference
  host environment record, and an inventory of 37 ignored runtime assets
  totaling about 438 MiB. The original USB remains a separate backup requirement.
- A temporary copy containing only Git-eligible DOFBOT files recreated its
  `.venv` and local kernel, resolved its own patched library, and passed all
  23 offline tests without using `~/yahboom-dofbot` or vendor runtime assets.
  It reused the current host's installed dependencies; this was not an erased-OS
  reinstallation or a validation of every optional notebook dependency.
- The documented `dtc`/`fdtoverlay` procedure compiled the source against the
  installed matching base DTB; `fdtget` returned `100000`. Only ignored local
  validation files were written, with no change to `/boot` or the active clock.
- `tools/check_setup.py --offline` verified dependency discovery and repo-local
  library resolution without constructing `Arm_Device` or opening a bus.
- Source recovery was checked with temporary fixtures: source/model files were
  preserved while IDE settings, editor backups/swaps, thumbnails and old eggs
  were excluded. The same junk is ignored by Git in the recovered vendor tree.
- Removed generated Python caches; preserved notebook checkpoints in dated
  backups under `~/yahboom-dofbot/backups/`. Working environments, model assets,
  current pose targets, and unrelated projects were preserved.
- Internal documentation links and setup-tool/basic-script syntax were checked.
  DOFBOT Git candidates total about 15.6 MiB with no individual file above 2 MiB.
- No movement commands, dependency installs, boot edits, commits or pushes were
  performed during this audit. New files must be committed and pushed before a
  GitHub clone will include them.
