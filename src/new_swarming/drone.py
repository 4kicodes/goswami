



import time

from loguru import logger
from pymavlink import mavutil

from .mesh import MeshNode
from .mavlink_client import MAVLinkClient


class Drone:

    def __init__(
        self,
        sysid,
        compid,
        port,
        master,
        state_store,
    ):

        self.sysid = sysid
        self.compid = compid
        self.port = port
        self.master = master

        self.state = state_store

        self.mesh = None

        self.mavlink = MAVLinkClient(
            master=self.master,
            sysid=self.sysid,
            state_store=self.state,
        )

    # ==================================================
    # START
    # ==================================================

    def start(self):

        self.mavlink.start()

        logger.success(
            f"[DRONE {self.sysid}] MAVLink started"
        )

    # ==================================================
    # MESH
    # ==================================================

    def enable_mesh(self, peer_sysids):

        self.mesh = MeshNode(
            self.sysid,
            self.port,
            peer_sysids,
        )

        self.mesh.start()

        logger.success(
            f"[DRONE {self.sysid}] Mesh enabled"
        )

        self.mesh.broadcast(
            "HELLO",
            {
                "sysid": self.sysid,
            },
        )

    # ==================================================
    # MODE
    # ==================================================

    def set_mode(
        self,
        mode: str,
        timeout: float = 10,
    ):

        try:

            mapping = self.master.mode_mapping()

            if mode not in mapping:

                logger.error(
                    f"[DRONE {self.sysid}] Unsupported mode {mode}"
                )

                return False

            logger.info(
                f"[DRONE {self.sysid}] Setting mode -> {mode}"
            )

            self.master.set_mode(
                mapping[mode]
            )

            if not self.mavlink.wait_for_mode(
                mode,
                timeout,
            ):

                logger.error(
                    f"[DRONE {self.sysid}] "
                    f"Mode change timeout ({mode})"
                )

                return False

            logger.success(
                f"[DRONE {self.sysid}] Mode confirmed -> {mode}"
            )

            return True

        except Exception as e:

            logger.error(
                f"[DRONE {self.sysid}] Mode change failed: {e}"
            )

            return False

    # ==================================================
    # ARM
    # ==================================================

    def arm(self):

        try:

            logger.info(
                f"[DRONE {self.sysid}] Arming"
            )

            self.master.arducopter_arm()

            if not self.mavlink.wait_until_armed():

                logger.error(
                    f"[DRONE {self.sysid}] Arm timeout"
                )

                return False

            logger.success(
                f"[DRONE {self.sysid}] Armed"
            )

            return True

        except Exception as e:

            logger.error(
                f"[DRONE {self.sysid}] Arm failed: {e}"
            )

            return False

    # ==================================================
    # TAKEOFF
    # ==================================================

    def takeoff(
        self,
        altitude=5.0,
        timeout=60,
    ):

        logger.info(
            f"[DRONE {self.sysid}] TAKEOFF START"
        )

        if not self.mavlink.is_connected():

            logger.error(
                f"[DRONE {self.sysid}] No MAVLink connection"
            )

            return False

        if not self.set_mode("GUIDED"):

            return False

        if not self.arm():

            return False

        try:

            self.master.mav.command_long_send(
                self.sysid,
                self.compid,
                mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                altitude,
            )

        except Exception as e:

            logger.error(
                f"[DRONE {self.sysid}] Takeoff command failed: {e}"
            )

            return False

        start = time.time()

        while time.time() - start < timeout:

            drone_state = self.state.get_drone(
                self.sysid
            )

            if drone_state:

                if drone_state.alt >= altitude * 0.95:

                    logger.success(
                        f"[DRONE {self.sysid}] AIRBORNE "
                        f"({drone_state.alt:.1f}m)"
                    )

                    return True

            time.sleep(0.2)

        logger.error(
            f"[DRONE {self.sysid}] TAKEOFF TIMEOUT"
        )

        return False

    # ==================================================
    # LAND
    # ==================================================

    def land(
        self,
        timeout=90,
    ):

        logger.info(
            f"[DRONE {self.sysid}] LANDING"
        )

        if not self.set_mode("LAND"):

            logger.error(
                f"[DRONE {self.sysid}] Failed to enter LAND mode"
            )

            return False

        start = time.time()

        touchdown_detected = False

        while time.time() - start < timeout:

            drone_state = self.state.get_drone(
                self.sysid
            )

            if drone_state is None:

                time.sleep(0.2)
                continue

            if drone_state.alt <= 0.2:

                touchdown_detected = True

            if (
                touchdown_detected
                and not drone_state.armed
            ):

                logger.success(
                    f"[DRONE {self.sysid}] LANDED"
                )

                return True

            time.sleep(0.2)

        logger.error(
            f"[DRONE {self.sysid}] LAND TIMEOUT"
        )

        return False

    # ==================================================
    # CONNECTION
    # ==================================================

    def is_connected(self):

        return self.mavlink.is_connected()

    # ==================================================
    # STOP
    # ==================================================

    def stop(self):

        try:

            if self.mesh:
                self.mesh.stop()

            self.mavlink.stop()

        except Exception as e:

            logger.error(
                f"[DRONE {self.sysid}] Stop failed: {e}"
            )

    # ==================================================
    # SNAPSHOT
    # ==================================================

    def snapshot(self):

        drone_state = self.state.get_drone(
            self.sysid
        )

        if drone_state is None:

            return {
                "sysid": self.sysid,
                "mode": "OFFLINE",
                "armed": False,
                "alt": 0.0,
                "battery": 0,
                "heading": 0.0,
            }

        return {
            "sysid": self.sysid,
            "mode": drone_state.mode,
            "armed": drone_state.armed,
            "alt": drone_state.alt,
            "battery": drone_state.battery,
            "heading": drone_state.heading,
        }