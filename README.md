# 🤖 Jetson Hobby Lab

My robotics and AI learning workspace on the **Jetson Orin Nano Super** with
Yahboom hardware, cameras, and a touchscreen.

I have been following **Paul McWhorter’s AI on Jetson Nano tutorials**, working
through Python and OpenCV exercises and adapting them to my Orin Nano setup.
The scripts in this repo cover camera basics, image processing, object tracking,
face recognition, and pan/tilt servo control. More recently, I cloned NVIDIA’s
**jetson-inference** and downloaded pretrained models including **AlexNet,
GoogLeNet, and ResNet-18** to continue exploring AI inference on the Jetson.

This is a personal learning lab: scripts, setup notes, and experiments evolve as
I work through the tutorials and connect more hardware.

---

## 🐍 Python and computer vision

The tutorial work and my adaptations live in [python_scripts/](python_scripts/README.md).
These experiments run directly on the Jetson host using Python.

| Folder | What I have been working on |
|---|---|
| [openCV/](python_scripts/openCV/) | Camera capture and recording, drawing, mouse input, HSV colors, masks, object tracking, and Haar cascade face detection |
| [faceRecognizer/](python_scripts/faceRecognizer/README.md) | Face detection and recognition with `face_recognition` and dlib, training data, live recognition, and threaded camera experiments |
| [PanTilt/](python_scripts/PanTilt/) | Color and face tracking with pan/tilt servo control |
| [servo/](python_scripts/servo/) | A Python interface and example for the Yahboom serial servo controller |

Recent work includes [twinCamLiveFace.py](python_scripts/faceRecognizer/twinCamLiveFace.py),
which captures two cameras in separate threads and displays their frames side by
side with an FPS counter.

**Run an OpenCV example** from the repo root:

```bash
cd ~/jetson-hobby-lab
export DISPLAY=:0
python3 python_scripts/openCV/TouchTracking.py
```

When launching over SSH, `DISPLAY=:0` targets the desktop on the Jetson’s attached
touchscreen. A desktop session must be running and permit access. Camera indices,
CSI camera pipelines, file paths, and serial ports may need adjusting for your
setup. See the [Python notes](python_scripts/README.md) and
[face recognition setup](python_scripts/faceRecognizer/README.md) for details.

---

## 🧠 jetson-inference and pretrained models

I recently cloned [NVIDIA jetson-inference](https://github.com/dusty-nv/jetson-inference)
into `jetson-inference/`. It is my next step from the Python/OpenCV tutorial work
into pretrained neural networks on the Jetson.

Downloaded model files are stored locally in `jetson-inference/data/networks/`:

| Models | Area to explore |
|---|---|
| AlexNet, GoogLeNet, ResNet-18 | Image classification |
| SSD-Mobilenet, SSD-Inception, DetectNet | Object detection |
| FCN-ResNet18 variants | Image segmentation |
| Pose-ResNet18 Body and Hand | Pose estimation |
| MonoDepth-FCN-Mobilenet | Depth estimation |

These files have been downloaded; running and testing the models is ongoing work.
The cloned `jetson-inference/` folder is ignored by Git, so it is **not included
in a fresh clone of this repo**. To recreate the local checkout:

```bash
cd ~/jetson-hobby-lab
git clone --recursive https://github.com/dusty-nv/jetson-inference.git
```

Follow the upstream repository’s build and setup instructions for your Jetson.

### 📦 Keep model downloads running after SSH disconnects

Keeping the Jetson powered on and connected to Wi-Fi alone does **not** guarantee
a download survives closing SSH. Start the download inside `tmux` on the Jetson:

```bash
sudo apt update && sudo apt install tmux
tmux new -s models
cd ~/jetson-hobby-lab/jetson-inference/tools
./download-models.sh
```

Detach with **Ctrl+B, then D** before disconnecting SSH. After reconnecting:

```bash
tmux attach -t models
```

To check for an existing download:

```bash
pgrep -af 'download-models|wget|curl'
```

---

## 🦾 DOFBOT robotic arm

The dedicated [dofbot/](dofbot/README.md) folder contains the tested Python servo
library, isolated Python/Jupyter launchers, recovered Yahboom manual notebooks,
and ROS application source. Start with its README for the 100 kHz boot setup,
query-only checks, manual examples, and the full application's remaining work.

- [Rebuild checklist and filesystem map](dofbot/docs/REBUILD.md): fresh clone,
  dependencies, boot overlay, validation, vendor assets, and Git backup.
- [Basic angle scripts](python_scripts/dofbot/README.md): read, write, read/write,
  and set a configured pose.

---

## 🦾 ROS 2 and Yahboom hardware

Alongside the AI tutorials, I have been experimenting with **Isaac ROS**, GPIO,
I2C, UART, and the Yahboom platform. The ROS setup uses an Isaac development
container for GPU/ROS work and host-side nodes for hardware access. The Python
vision experiments above also run on the host.

The last recorded ROS/hardware checkpoint was **2026-08-16**:

| Area | Recorded status / next step |
|---|---|
| Isaac ROS container | Working; `check-env.sh` passed 8/8 checks |
| GPIO input | Host node publishes; container reads the topic |
| GPIO output | Untested with the Yahboom hat seated; unseat it before loopback testing |
| OLED | SH1106, 128×64, I2C bus 7 at `0x3c`; text renders but the top rows are clipped |
| Expansion MCU | Register map at `0x0e` still needs investigation |
| UART for host ROS | At that checkpoint, `dialout` access and `pyserial` still needed setup |

For the OLED, the next debugging steps are to check line spacing, top margin,
and display offset in [scripts/oled_write.py](scripts/oled_write.py).
The host ROS installation was partial: `rclpy` worked, but the `ros2` CLI and
`launch_ros` were unavailable. See [host_ws/README.md](host_ws/README.md) for
host-node commands and setup notes.

**Start the Isaac ROS container:**

```bash
~/jetson-hobby-lab/docker/isaac-ros-humble/run.sh
# Inside the container:
/host_scripts/check-env.sh
```

The launcher requires `isaac_ros_common` in `isaac_ros_ws/src/`. For first setup:

```bash
cd ~/jetson-hobby-lab/isaac_ros_ws/src
git clone -b release-3.2 https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_common.git
```

The launcher applies a CUDA permission fix; details are in
[scripts/fix-gpu-perms.sh](scripts/fix-gpu-perms.sh).

**Check host hardware or write to the OLED:**

```bash
cd ~/jetson-hobby-lab
./scripts/check-gpio.sh
./scripts/oled_write.py "Hello" "Jetson"
```

---

## 🗂️ Repository layout

```text
jetson-hobby-lab/
├── dofbot/                  # DOFBOT library, manual notebooks, diagnostics and setup
├── python_scripts/           # Paul McWhorter tutorial work and my Python experiments
├── jetson-inference/         # local NVIDIA checkout and downloaded models (ignored)
├── docker/isaac-ros-humble/  # Isaac ROS container launcher and shell configuration
├── isaac_ros_ws/             # workspace mounted into the Isaac ROS container
├── ros2_ws/                  # additional ROS 2 workspace
├── host_ws/                  # host-side ROS hardware nodes
├── scripts/                  # environment checks, GPIO checks, OLED, GPU permissions
├── setup/                    # host configuration files
└── Yahboom_firmware/         # servo controller firmware and control code
```

Large downloads and generated data stay local: `jetson-inference/`, dlib source
and its archive, `installSwapfile/`, face photos and training data, recordings,
and ROS build output are excluded through [.gitignore](.gitignore).
A fresh clone needs its own dependencies, model downloads, and face data.

---

## 🔗 References

- **Paul McWhorter’s AI on Jetson Nano tutorials** — the basis for my Python and computer vision learning
- [NVIDIA jetson-inference](https://github.com/dusty-nv/jetson-inference)
- [OpenCV Python tutorials](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html)
- [face_recognition](https://github.com/ageitgey/face_recognition)
- [Isaac ROS docs](https://nvidia-isaac-ros.github.io/)
- [Yahboom Orin Nano course](https://www.yahboom.net/study/Orin-Nano-SUPER)
- [Jetson.GPIO](https://github.com/NVIDIA/jetson-gpio)
