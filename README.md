# PX4 + ROS 2 + RL Demo Pipeline

A minimal, working stack for hooking a machine-learning / RL policy up to a
simulated PX4 drone: **PX4 SITL + Gazebo** talks to **ROS 2 Humble** over
**uXRCE-DDS**, and a ROS 2 node (`agere_rl`) subscribes to vehicle state and
publishes offboard setpoints. This is the seam you plug a trained policy into.

```
┌─────────────────────────────┐        UDP 8888          ┌──────────────────────────────┐
│        px4-gazebo           │ ◄──────────────────────► │        ros2-bridge           │
│  PX4 SITL + Gazebo sim      │   uXRCE-DDS / /fmu/*     │  ROS 2 Humble + agere_rl     │
│  + MicroXRCEAgent           │                          │  (your RL / control code)    │
└─────────────────────────────┘                          └──────────────────────────────┘
              ▲
              │ optional
              ▼
┌─────────────────────────────┐
│      qgroundcontrol         │  visual monitoring / manual override
└─────────────────────────────┘
```

## Contents

- `Dockerfile.px4` — builds PX4 SITL + Gazebo + MicroXRCEAgent (image `px4-demo:latest`)
- `Dockerfile.ros2` — builds ROS 2 Humble + `px4_msgs`/`px4_ros_com` + your `agere_rl` package (image `ros2-bridge:latest`)
- `docker-compose.yml` — wires all three services together
- `run.sh` — convenience wrapper around `docker compose` (start/stop/logs/shell/test/build/clean)
- `src/` — the `agere_rl` ROS 2 package (this is what gets bind-mounted into the ros2-bridge container)
  - `agere_rl/rl_agent.py` — arms the vehicle, engages Offboard mode, publishes setpoints (**your policy plugs in here**)
  - `agere_rl/test_node.py` — sanity-check subscriber for `/fmu/out/vehicle_attitude`
  - `package.xml`, `setup.py`, `setup.cfg`, `resource/agere_rl` — standard `ament_python` package scaffolding

## Prerequisites

- Docker + Docker Compose v2 (`docker compose`, not the old `docker-compose`)
- Linux host with an X server, if you want Gazebo/QGroundControl GUI windows (`xhost +local:docker`)
- `network_mode: host` is used throughout, so this is **Linux-only** as written — Docker Desktop on Mac/Windows doesn't support host networking the same way

## How the pieces talk to each other

- PX4 SITL publishes/subscribes on topics like `/fmu/out/vehicle_attitude`,
  `/fmu/out/vehicle_local_position`, `/fmu/in/trajectory_setpoint`, etc.,
  bridged into ROS 2 by `MicroXRCEAgent` (UDP port 8888) + PX4's uXRCE-DDS client.
- All `/fmu/out/*` topics are published by PX4 as **best-effort, volatile**
  QoS. Any ROS 2 subscriber must use matching QoS or it will connect but
  silently receive nothing — both nodes in `agere_rl` already do this.
- PX4 will not accept `TrajectorySetpoint` messages unless it is also
  continuously receiving `OffboardControlMode` (a "yes, offboard control is
  active" heartbeat, published at 10 Hz here) — `rl_agent.py` handles this,
  then arms and requests Offboard mode once PX4 has seen enough setpoints.

## Build

### Option A — Docker Compose (recommended)

Build all images:
```bash
docker compose build
```

Build a single image:
```bash
docker compose build px4-gazebo
docker compose build ros2-bridge
```

Force a clean rebuild (no layer cache):
```bash
docker compose build --no-cache
```

### Option B — Plain `docker build`

```bash
docker build -f Dockerfile.px4  -t px4-demo:latest .
docker build -f Dockerfile.ros2 -t ros2-bridge:latest .
```

### Option C — `run.sh`

```bash
./run.sh build     # docker compose build --no-cache
```
`./run.sh start` will also build automatically if the images don't exist yet.

## Run

### Option A — Docker Compose (recommended)

Start everything in the background:
```bash
docker compose up -d
```

Start only the simulator + bridge, without QGroundControl (it's behind a
Compose "profile" so it doesn't start by default):
```bash
docker compose up -d px4-gazebo ros2-bridge
```

Start with QGroundControl included:
```bash
docker compose --profile full up -d
```

Watch logs:
```bash
docker compose logs -f
```

Stop everything:
```bash
docker compose down
```

**What starts, in order:**
1. `px4-gazebo` builds/starts, launches `MicroXRCEAgent` on UDP 8888, then PX4 SITL + Gazebo.
2. `ros2-bridge` waits for `px4-gazebo`'s healthcheck (`pgrep px4`) to pass, then starts. Its entrypoint rebuilds the `agere_rl` package (it's bind-mounted from `./src`, so it doesn't exist yet when the image itself was built) and sources the workspace.
3. `qgroundcontrol` (optional, `full` profile only) gives you a GUI to watch/override the vehicle.

### Option B — Plain `docker run`

PX4 + Gazebo (needs the X socket mounted for the GUI):
```bash
docker run --rm -it --network=host \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    px4-demo:latest
```

ROS 2 bridge, with your `agere_rl` source mounted in and a shell you can work from:
```bash
docker run --rm -it --network=host \
    -v "$(pwd)/src:/root/colcon_ws/src/agere_rl:rw" \
    ros2-bridge:latest /entrypoint.sh bash
```

You'll need PX4 already running (from the command above, or via Compose) since
this container only holds the ROS 2 side of the bridge.

### Option C — `run.sh`

```bash
./run.sh start              # build if needed, then docker compose up -d
./run.sh status             # docker compose ps
./run.sh logs                # tail all logs
./run.sh shell ros2-bridge   # docker exec -it ros2-bridge bash
./run.sh shell px4-gazebo    # docker exec -it px4-gazebo bash — note: container name is px4-demo, see caveat below
./run.sh test                # checks /fmu topics exist and echoes one attitude message
./run.sh stop
./run.sh restart
./run.sh clean               # docker compose down -v --rmi all
```

> **Caveat:** `docker-compose.yml` names the PX4 container `px4-demo`, but
> `run.sh shell` expects you to pass `px4-gazebo` (the *service* name) as the
> container name. Use `./run.sh shell px4-demo` instead, or `docker exec -it px4-demo bash` directly.

## Running the RL agent / test node

Once the stack is up, exec into the ROS 2 bridge and run either node (the
`ros2 run` names come from the entry points in `src/setup.py`):

```bash
docker exec -it ros2-bridge bash
source /opt/ros/humble/setup.bash
source /root/colcon_ws/install/setup.bash

ros2 run agere_rl test_node   # sanity check: prints attitude quaternion as it streams in
ros2 run agere_rl rl_agent    # arms, engages offboard mode, holds a hover setpoint
```

If you edit files under `src/` on the host, they're live-mounted into the
container — rerun `colcon build --packages-select agere_rl` inside the
container (or restart it, since the entrypoint does this automatically) to
pick up changes.

## Plugging in an ML/RL policy

`rl_agent.py` is deliberately the smallest thing that gets PX4 into a state
where it will accept commands:

- `self.current_state` holds the latest attitude quaternion and local
  position as they stream in from PX4.
- `publish_setpoint()` currently just holds a fixed hover altitude — replace
  its body with your policy's output (e.g. compute a `TrajectorySetpoint`
  from `self.current_state` using a loaded model) and everything else
  (heartbeat, arming, mode switch) keeps working unchanged.
- If your policy needs velocity/attitude-rate control instead of position
  setpoints, flip the corresponding fields in `OffboardControlMode`
  (`velocity`/`attitude`/`body_rate`) and populate the matching fields on
  `TrajectorySetpoint` (or switch to `VehicleAttitudeSetpoint`/`VehicleRatesSetpoint`).

## Known limitations / things to verify yourself

- `Dockerfile.px4` overrides `px4io/px4-sitl-gazebo`'s own entrypoint and
  directly execs the `px4` binary. That base image normally expects to be
  run via its own launch logic (env vars like `PX4_SIM_MODEL`/`PX4_GZ_WORLD`
  for world/model spawning); bypassing it may mean Gazebo doesn't spawn the
  world you expect. Worth checking `docker compose logs px4-gazebo` for a
  Gazebo window/world actually coming up, not just the PX4 shell banner.
- `ros2-bridge`'s Compose service runs `command: /entrypoint.sh bash` with no
  TTY attached under `docker compose up -d`, so that shell process will exit
  right after the build/status output and the container will restart in a
  loop (harmless, since your workflow is `docker exec -it ros2-bridge bash`
  afterward anyway — but the constant restarting in `docker compose ps` is expected, not a bug to chase).
- Everything uses `network_mode: host`, so this only runs correctly on Linux.
