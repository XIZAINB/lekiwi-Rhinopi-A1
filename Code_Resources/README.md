# LeKiwi_A1 · Code_Resources (Deployment & Teleoperation)

> Full deployment guide for running the **[LeKiwi](https://github.com/huggingface/lerobot)** host on a **Rhino Pi A1 (AidLux / ARM64)** — board environment, serial port/camera detection, calibration, zero alignment, and troubleshooting.
>
> One-command setup for running the LeKiwi robot host on a Rhino Pi A1 (AidLux, ARM64), including calibration and leader-arm zero-alignment helpers.

> Repository URL: <https://github.com/XIZAINB/lekiwi-Rhinopi-A1>.
> This directory is the **software part** (`Code_Resources/`) of the main `LeKiwi_A1/` repo; all commands below assume you have already `cd`-ed into this directory.

---

## 1. What This Is

A fresh board + a fresh PC. After `git clone`:

| Stage | What it does | Commands | Verified |
| --- | --- | --- | --- |
| **T1** | Board environment + start host | `a1_bootstrap.sh` → `a1_host.sh start` | ✅ |
| **T2** | PC environment + keyboard control of base | `win_bootstrap.ps1` → `teleop.ps1 -Keyboard` | ✅ |
| **T3** | Connect leader arm, calibrate + zero-align, then teleoperate by dragging | `win_calibrate.ps1` → `zero_align.ps1` → `teleop.ps1` | ✅ |
| **T4** | Readable error messages for abnormal scenarios (unplugged cable / host not started) | — | ⬜ |

> Tested environment: Rhino Pi A1 (Ubuntu 24.04.3 / aarch64) + Windows 11 + SO100 leader arm, 2026-10-30.
> See Section 7 "Tested Versions" and `docs/troubleshooting.md` for details.

## 2. What This Is NOT (Important Boundaries)

- ❌ **Does not include calibration files.** `homing_offset` is **unique to each robot and each assembly**, so it cannot be distributed with the repo.
  → The scripts handle "environment + config + startup + self-check"; calibration runs through a **guided, interactive flow** where a human positions the arm and presses Enter.
- ✅ Hardware documentation lives in the **parent directory of this repo**: [BOM](../BOM.md), [3D printed parts](../3D_Printing_Models/), [assembly steps](../Assembly_Steps_and_Structure_Diagram/Assembly_Steps.md), [wiring diagram](../Wiring_Diagram/Wiring_diagram.png), [servo ID setup](../Set_Servo_ID/Set_Servo_ID.md) (from [SIGRobotics-UIUC/LeKiwi](https://github.com/SIGRobotics-UIUC/LeKiwi)).
- ❌ Does not include the servo vendor's debug software/PDFs. Download them from the vendor's website.
- ❌ Does not modify the lerobot source. `lerobot` is checked out as-is at a fixed commit; this repo only handles configuration and orchestration.

> `upstream/lerobot-main/` is a **source snapshot** of lerobot at a fixed commit, provided only for reading/reference convenience (e.g., to look at the original implementation of `examples/lekiwi/`). **It is not used at runtime**: both ends are cloned separately by the bootstrap scripts to `$HOME/lerobot` (board side) / a local directory (PC side), with the path set by `LEROBOT_DIR` in `config/env`.
> The snapshot is about 87 MB, with media files tracked via Git LFS. If you only want to run the scripts and skip the snapshot, clone with `GIT_LFS_SKIP_SMUDGE=1 git clone ...`.

> This repository is not a fork. `scripts/teleoperate.py` and `scripts/teleoperate_keyboard_only.py`
> are derived files from lerobot `examples/lekiwi/` (Apache-2.0, with the original header retained and modifications noted).
> The upstream `examples/lekiwi/teleoperate.py` hardcodes `remote_ip` / `port` inside `main()` with no CLI arguments,
> so the only way was to copy it and modify — this is the only **modified** upstream code in this repo (the snapshot in `upstream/` is an unmodified copy, not a single line changed).

---

## 3. Prerequisites

### Hardware

- Rhino Pi A1 (tested with Ubuntu 24.04.3 LTS / aarch64; AidLux-based systems also work)
- LeKiwi base + SO100/101 follower arm + 9 Feetech STS3215 servos (IDs 1–9 already configured)
- **Base battery powered on** — servos and wheels are powered by the base battery; USB only powers the adapter board.
  Without power, `FeetechMotorsBus.scan_port()` returns an empty dict and the host reports `Missing motor IDs: 1~9`
- USB adapter board (servo bus), USB camera (wrist)
- Leader arm + CH343/CH340 USB cable (only needed for T3)

### Software

- Board: `git`, `curl`, internet access (to install `uv` and Python dependencies)
- PC: Windows 10/11 + PowerShell 5.1; `ssh` required

### Network

The board and PC must be on the **same subnet**, and the router must not have AP isolation enabled. Get the board IP with `hostname -I` (DHCP by default; it can change).

---

## 4. Quick Start

### Step 1 · Board side (T1)

```bash
ssh <BOARD_USER>@<BOARD_IP>

git clone https://github.com/XIZAINB/lekiwi-Rhinopi-A1.git ~/LeKiwi_A1
cd ~/LeKiwi_A1/Code_Resources

# One-time environment setup (re-runnable): apt deps → uv → clone lerobot@<commit> → uv sync → slim → self-check
sh scripts/a1_bootstrap.sh
```

The script automatically generates `config/env` (copied from `env.example`). **It is the only file you need to edit**:

```bash
vi config/env          # Key items: CAMERA_WRIST (run sh scripts/a1_detect.sh first to get a suggested value)
sh scripts/a1_detect.sh
```

> The script automatically "slims" the venv: it swaps the CUDA torch build for a CPU build and strips `nvidia`/`cuda`/`triton`.
> The A1 has no NVIDIA GPU; without slimming, `uv sync` would download ~3.4 GB extra.
> Measured venv size dropped from **4.7 GB to 848 MB**, with teleoperation unaffected. To skip slimming: `SLIM_VENV=0 sh scripts/a1_bootstrap.sh`.

The follower must be calibrated the first time (interactive; the script will tell you how to position the arm). Calibration is **skipped automatically** when a calibration file already exists; force a recalibration with `--recalibrate`:

```bash
sh scripts/a1_calibrate.sh                # Only enters the pose flow if no calibration file exists
sh scripts/a1_calibrate.sh --recalibrate  # Force recalibration
```

Start the host:

```bash
sh scripts/a1_host.sh start     # Start in the background
sh scripts/a1_host.sh status    # Show process + log tail
sh scripts/a1_host.sh log       # tail -f
sh scripts/a1_host.sh stop      # Stop (torque stays engaged, see below)
```

Success is indicated by `[ok] host ready (ZMQ port 5555 listening)`.

> Readiness is determined by **port listening** state, not log text — upstream prints `Waiting for commands...` at INFO level, which is suppressed by default.

> `a1_host.sh stop` force-kills the process and **does not release torque**; the arm stays locked.
> To manually re-position the arm, run: `sh scripts/a1_host.sh release-torque`

### Step 2 · PC side (T2)

```powershell
git clone https://github.com/XIZAINB/lekiwi-Rhinopi-A1.git C:\LeKiwi_A1
cd C:\LeKiwi_A1\Code_Resources

# One-time environment setup (re-runnable): uv → clone lerobot → uv sync → detect COM ports → self-check
powershell -ExecutionPolicy Bypass -File scripts\win_bootstrap.ps1
```

Edit `config\env` and fill in the board info:

```ini
BOARD_IP=192.168.1.100
BOARD_USER=aidlux
```

Verify the base and camera with keyboard-only control first (no leader arm needed):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\teleop.ps1 -Keyboard
```

| Key | Action |
| --- | --- |
| `w` / `s` | Forward / backward |
| `a` / `d` | Strafe left / right |
| `z` / `x` | Turn left / right in place |
| `r` / `f` | Speed up / slow down (0.1 / 0.2 / 0.3 m/s) |
| `Ctrl+C` | Exit (base auto-stops via host watchdog within 0.5 s) |

> To also view the wrist camera feed, add `-Rerun`: `teleop.ps1 -Keyboard -Rerun` (or set `SHOW_RERUN=1` in `config/env`).
> Keyboard-only mode does **not** open a visualization window by default.

### Step 3 · Connect the leader arm (T3)

```powershell
# 1) Leader serial port (changes with USB port; double-check)
powershell -ExecutionPolicy Bypass -File scripts\win_bootstrap.ps1 -DetectOnly

# 2) Leader calibration (press Enter manually; the script will prompt)
powershell -ExecutionPolicy Bypass -File scripts\win_calibrate.ps1

# 3) Zero alignment: release torque → pose both arms identically → measure/align/re-verify in one command
powershell -ExecutionPolicy Bypass -File scripts\zero_align.ps1

# 4) Teleoperate
powershell -ExecutionPolicy Bypass -File scripts\teleop.ps1
```

> **After recalibrating either side, you MUST re-run `zero_align.ps1`**, otherwise teleoperation will show a fixed angular offset.

---

## 4.1 Daily Command Cheat Sheet (after setup)

| Purpose | Command |
| --- | --- |
| Start host | `ssh aidlux@<IP> "cd ~/LeKiwi_A1/Code_Resources && sh scripts/a1_host.sh start"` |
| Stop host | `ssh aidlux@<IP> "cd ~/LeKiwi_A1/Code_Resources && sh scripts/a1_host.sh stop"` |
| View logs | `ssh aidlux@<IP> "tail -f ~/host.log"` |
| Release torque | `ssh aidlux@<IP> "cd ~/LeKiwi_A1/Code_Resources && sh scripts/a1_host.sh release-torque"` |
| Keyboard teleop | `powershell -ExecutionPolicy Bypass -File scripts\teleop.ps1 -Keyboard -Rerun` |
| Leader teleop | `powershell -ExecutionPolicy Bypass -File scripts\teleop.ps1` |
| Re-align | `powershell -ExecutionPolicy Bypass -File scripts\zero_align.ps1` |
| Restart host (stop, then start) | `ssh aidlux@<IP> "cd ~/LeKiwi_A1/Code_Resources && sh scripts/a1_host.sh stop && sh scripts/a1_host.sh start"` |

---

## 4.2 Restarting After Shutting Down

`a1_bootstrap.sh` / `win_bootstrap.ps1` (environment) and `a1_calibrate.sh` / `win_calibrate.ps1` + `zero_align.ps1` (calibration)
**only need to be done once**. After that, each time you restart, only do the following — order matters: **start the board host first, then the PC teleoperation**.

### Case A · Only the PC side was shut down (`Ctrl+C` or closed the PowerShell window)

The host is still running on the board; just reconnect:

```powershell
cd \LeKiwi_A1\Code_Resources
powershell -ExecutionPolicy Bypass -File scripts\teleop.ps1               # leader arm + keyboard base
powershell -ExecutionPolicy Bypass -File scripts\teleop.ps1 -Keyboard     # keyboard only
```

### Case B · The host is also stopped (ran stop / the board rebooted / the host lifetime expired)

Start the board host first; `start` returns `[ok] host ready` only after port 5555 is listening:

```powershell
ssh aidlux@192.168.112.249 "cd ~/LeKiwi_A1/Code_Resources && sh scripts/a1_host.sh start"
```

Then run the Case A commands. You can also log into the board and operate there:

```bash
ssh aidlux@192.168.112.249
cd ~/LeKiwi_A1/Code_Resources
sh scripts/a1_host.sh status    # First confirm whether it's already running
sh scripts/a1_host.sh start
```

> - If a host is already running, `start` will report "host is already running" and exit non-zero — that's not a failure; if `status` shows the process, don't start it again.
> - To truly restart, `stop` first then `start` (the script has no separate `restart` subcommand).
> - `CONNECTION_TIME_S=3600` is the host's **total lifetime**, counted from `start`; it exits by itself after 1 hour (upstream default is only 30 s).
>   This is normal behavior; just restart per Case B.

### Case C · Board lost power / can't connect after a network change (DHCP assigned a new IP)

The board IP is assigned by DHCP and can change (currently measured as `192.168.112.249`). If the connection fails, check the IP first, then update the PC-side config:

```bash
ssh aidlux@192.168.112.249 "hostname -I"     # 1) Get the board's current IP
```

```powershell
# 2) Write the new IP into BOARD_IP in config\env on the PC, then verify the port
Test-NetConnection 192.168.112.249 -Port 5555
```

Once it's reachable, start per Case A / B. If `teleop.ps1` can't connect, it will directly prompt "Did the IP change?" and print the board-side start command.

### What Must Be Redone After Shutdown & Restart?

| Action | Must be redone after restart? |
| --- | --- |
| Power on the base battery | **Yes** — USB doesn't power the servos; without power the host reports `Missing motor IDs: 1~9` |
| `a1_host.sh start` | **Yes** — the host is not a systemd service and does not auto-start on boot |
| `a1_bootstrap.sh` / `win_bootstrap.ps1` | No — only run when changing boards / PCs / upgrading lerobot |
| Follower / leader calibration | No — calibration files are stored on disk; only redo after replacing servos or changing servo IDs |
| `zero_align.ps1` | No — only run after recalibration, disassembling servos, or when a fixed offset appears |
| Check `LEADER_PORT` | Only when the USB port changed: `win_bootstrap.ps1 -DetectOnly` |

Calibration file locations (they survive reboots and power loss):

- Board-side follower: `~/.cache/huggingface/lerobot/calibration/robots/lekiwi/<ROBOT_ID>.json`
- PC-side leader: `%USERPROFILE%\.cache\huggingface\lerobot\calibration\teleoperators\so_leader\<LEADER_ID>.json`

### Recommended Shutdown Order

1. `Ctrl+C` on the PC to exit teleoperation (base auto-stops via the host watchdog within 0.5 s)
2. (Optional) `sh scripts/a1_host.sh stop` on the board
3. Disconnect the base battery

> `stop` force-kills and **does not release torque**. To move the arm back to its home pose before finishing, run `stop` first, then `sh scripts/a1_host.sh release-torque`.

---

## 5. Configuration (`config/env`)

A single file shared by shell / Python / PowerShell (PowerShell parses it via a script; there is no separate `env.ps1` anymore).

| Key | Default | Description |
| --- | --- | --- |
| `BOARD_IP` | — | Board IP |
| `BOARD_USER` | `aidlux` | SSH user |
| `BOARD_REPO` | `$HOME/LeKiwi_A1/Code_Resources` | Path to this repo on the board |
| `LEROBOT_DIR` | `$HOME/lerobot` | Path to the lerobot code |
| `LEROBOT_COMMIT` | `53feaef` | Pinned lerobot commit (must match on both ends) |
| `ROBOT_ID` | `my_kiwi` | Calibration ID for the follower (board side) |
| `ROBOT_PORT` | `/dev/ttyACM0` | Servo bus serial port (board side) |
| `CAMERA_WRIST` | empty | Wrist camera; **leave empty = camera disabled** |
| `CAMERA_FPS` / `CAMERA_WIDTH` / `CAMERA_HEIGHT` / `CAMERA_ROTATE` | `30 / 480 / 640 / 90` | Camera parameters |
| `ZMQ_CMD_PORT` / `ZMQ_OBS_PORT` | `5555 / 5556` | ZMQ ports |
| `CONNECTION_TIME_S` | `3600` | Host lifetime (default 30 s exits automatically) |
| `CLIENT_ID` | `my_lekiwi` | Local identifier of the control end |
| `LEADER_PORT` | `COM11` | Leader serial port (PC side) |
| `LEADER_ID` | `my_awesome_leader_arm` | Leader calibration ID |
| `SLIM_VENV` | `1` | Board-side slimming (swap to CPU torch + strip CUDA); `0` disables |
| `ARM_HOLD_DEADBAND` | `0.5` | Keyboard-only mode: write-back deadband (degrees); changes below this don't update the target |
| `ARM_HOLD_ALPHA` | `0.6` | Keyboard-only mode: EMA smoothing factor (smaller = steadier but slower) |
| `ARM_HOLD_MAX_JUMP` | `10.0` | Keyboard-only mode: single-frame jumps above this are treated as garbled bus packets and dropped |
| `SHOW_RERUN` | `0` | `1` = open the rerun visualization window by default |
| `MAX_RELATIVE_TARGET` | empty | Max per-step delta; empty = unlimited |

> To temporarily override a value, just set an environment variable with the same name (e.g., `ROBOT_PORT=/dev/ttyACM1 sh scripts/a1_host.sh start`).

---

## 6. Acceptance (run before release/delivery)

- [x] **T1**: On a fresh A1, `a1_bootstrap.sh` runs through and `a1_host.sh start` reports "host ready"; `Test-NetConnection <BOARD_IP> -Port 5555/5556` returns True on the PC
- [x] **T2**: `teleop.ps1 -Keyboard` controls the base; `-Rerun` shows video
- [x] **T3**: After leader calibration + zero alignment, dragging the arm shows no fixed offset (measured residual 0.13°)
- [ ] **T4**: Unplugging the camera / network cable / host not started — scripts give **human-readable errors** instead of a traceback

> Having trouble? Start with [`docs/troubleshooting.md`](docs/troubleshooting.md) (four categories — board / connection / calibration / maintenance — with 20+ tested pitfalls).

---

## 7. Tested Versions

| Component | Version |
| --- | --- |
| lerobot | commit `53feaef` |
| Board | Rhino Pi A1 (Ubuntu 24.04.3 / kernel 6.6.65-qli, aarch64) |
| Python (board) | 3.12.3 (managed by `uv`) |
| torch (board) | `2.8.0+cpu` (after slimming, `cuda_available: False`) |
| uv | 0.13.6 |
| Board venv size | 848 MB (4.7 GB before slimming) |
| Leader arm | SO100 leader + CH343 (`COM11`) |
| Zero alignment measured | Max offset 12.48° before alignment (`wrist_roll`) → **0.13° residual** after |
| PC | Windows 11 + PowerShell 5.1 |

> The version matrix is based on the self-check output at the end of `sh scripts/a1_bootstrap.sh`; run T1–T4 before upgrading lerobot.

---

## 8. Known Limitations & Unverified Items

- **T4 error-path not verified**: the friendliness of error messages (unplugged USB / network / host not started) hasn't been systematically tested
- **Fresh-clone full install not yet run**: T2 acceptance reused an existing venv (fast path); the full from-scratch `win_bootstrap.ps1` install path needs verification
- **No dataset recording/training/evaluation**: the upstream `record.py` / `replay.py` / `evaluate.py` already cover this; this repo stops at teleoperation
- **Only one camera verified**: `CAMERA_WRIST` only; multiple cameras require extending `a1_host.py::build_cameras()` yourself
- **Control ends other than Windows base not covered**: macOS / Linux control ends untested
- **`a1_slim_venv.sh` after `uv sync` is idempotent**, but every `a1_bootstrap.sh` re-installs and re-slims (using the local cache, so it's not slow)

---

## 9. Directory Structure

```
.
├── README.md
├── LICENSE                    # Apache-2.0
├── .gitattributes             # Locks *.sh/*.py = LF, *.ps1 = CRLF
├── config/
│   ├── env.example            # Template; bootstrap copies it to config/env (gitignored)
│   └── env                    # Local config (not committed)
├── scripts/
│   ├── _env.py / _env.ps1     # config/env reader (shared by sh/py/ps)
│   ├── a1_bootstrap.sh        # Board: apt → uv → clone lerobot@commit → sync → slim → self-check
│   ├── a1_slim_venv.sh        # Board: CUDA torch → CPU torch, strip nvidia/cuda/triton
│   ├── a1_detect.sh           # Board: serial / camera detection, outputs suggested config
│   ├── a1_calibrate.sh/.py    # Board: follower calibration guide (cameras={} — no camera dependency)
│   ├── a1_host.sh             # Board: start / stop / status / log / release-torque
│   ├── a1_host.py             # Board: reads config/env and starts the host (no upstream source changes)
│   ├── win_bootstrap.ps1      # PC: environment setup + COM port detection + self-check
│   ├── win_calibrate.ps1      # PC: leader calibration guide
│   ├── teleop.ps1             # PC: teleoperation entry point (-Keyboard / -Rerun)
│   ├── zero_align.ps1         # PC: one-command zero alignment
│   ├── teleoperate.py         # Upstream-derived: reads config/env + image downsampling (LOG_FPS=5)
│   ├── teleoperate_keyboard_only.py  # Upstream-derived: keyboard-only + three-stage filtering
│   ├── align_leader_to_follower.py   # Zero alignment algorithm (supports --dry-run)
│   ├── measure_offset_once.py        # Read-only offset measurement (= align --dry-run)
│   └── release_torque.py             # Board: release torque
├── docs/
│   └── troubleshooting.md     # Tested pitfall table (board / connection / calibration / maintenance)
└── upstream/
    └── lerobot-main/          # lerobot source snapshot at a fixed commit (read-only reference, not used at runtime)
```

---

## 10. License

Apache-2.0, see [LICENSE](LICENSE). lerobot is Apache-2.0; the hardware design belongs to SIGRobotics-UIUC/LeKiwi.
