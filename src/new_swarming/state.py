from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Optional
import time


# ==================================================
# DRONE STATE
# ==================================================

@dataclass
class DroneState:
    sysid: int
    armed: bool = False
    mode: str = "INIT"

    lat: float = 0.0
    lon: float = 0.0
    alt: float = 0.0

    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0

    heading: float = 0.0
    battery: int = 100

    last_update: float = field(default_factory=time.time)


# ==================================================
# MESH STATE
# ==================================================

@dataclass
class MeshState:
    peers: Dict[int, float] = field(default_factory=dict)
    messages: int = 0


# ==================================================
# SWARM STATE
# ==================================================

@dataclass
class SwarmState:
    leader_id: Optional[int] = None
    mode: str = "IDLE"


# ==================================================
# THREAD SAFE WRAPPER
# ==================================================

class StateStore:

    def __init__(self):
        self.lock = Lock()

        self.drone_states: Dict[int, DroneState] = {}
        self.mesh_states: Dict[int, MeshState] = {}

        self.swarm_state = SwarmState()

    # ==================================================
    # UPDATE
    # ==================================================

    def update_drone(self, sysid: int, **kwargs):

        with self.lock:

            if sysid not in self.drone_states:
                self.drone_states[sysid] = DroneState(sysid)

            state = self.drone_states[sysid]

            for k, v in kwargs.items():

                if hasattr(state, k):
                    setattr(state, k, v)

            state.last_update = time.time()

    # ==================================================
    # GET SINGLE DRONE
    # ==================================================

    def get_drone(self, sysid: int):

        with self.lock:

            return self.drone_states.get(sysid)

    # ==================================================
    # DRONE ONLINE?
    # ==================================================

    def is_stale(
        self,
        sysid: int,
        timeout: float = 3.0,
    ):

        with self.lock:

            state = self.drone_states.get(sysid)

            if state is None:
                return True

            return (
                time.time()
                - state.last_update
            ) > timeout

    # ==================================================
    # SNAPSHOT
    # ==================================================

    def get_snapshot(self):

        with self.lock:

            return (
                dict(self.drone_states),
                dict(self.mesh_states),
                self.swarm_state,
            )