import queue
import threading
import time

from loguru import logger
from pymavlink import mavutil


class MAVLinkClient:

    def __init__(
        self,
        master,
        sysid,
        state_store,
    ):

        self.master = master
        self.sysid = sysid
        self.state = state_store

        self.running = False
        self.thread = None

        self.ack_queue = queue.Queue()
        self.event_queue = queue.Queue()

        self.last_heartbeat = 0.0

    # ==================================================
    # START
    # ==================================================

    def start(self):

        if self.running:
            return

        self.running = True

        self.thread = threading.Thread(
            target=self._rx_loop,
            daemon=True,
            name=f"mavlink-{self.sysid}",
        )

        self.thread.start()

        logger.success(
            f"[MAVLINK {self.sysid}] RX thread started"
        )

    # ==================================================
    # STOP
    # ==================================================

    def stop(self):

        self.running = False

        if self.thread:
            self.thread.join(timeout=2)

    # ==================================================
    # RX LOOP
    # ==================================================

    def _rx_loop(self):

        while self.running:

            try:

                msg = self.master.recv_match(
                    blocking=True,
                    timeout=1,
                )

                if msg is None:
                    continue

                self._process_message(msg)

            except Exception as e:

                if self.running:

                    logger.error(
                        f"[MAVLINK {self.sysid}] RX error: {e}"
                    )

    # ==================================================
    # MESSAGE ROUTER
    # ==================================================

    def _process_message(self, msg):

        msg_type = msg.get_type()

        # --------------------------------------------------
        # HEARTBEAT
        # --------------------------------------------------

        if msg_type == "HEARTBEAT":

            self.last_heartbeat = time.time()

            armed = bool(
                msg.base_mode
                & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
            )

            try:

                mode = mavutil.mode_string_v10(msg)

            except Exception:

                mode = "UNKNOWN"

            self.state.update_drone(
                self.sysid,
                armed=armed,
                mode=mode,
            )

            self.event_queue.put(msg)

        # --------------------------------------------------
        # POSITION
        # --------------------------------------------------

        elif msg_type == "GLOBAL_POSITION_INT":

            self.state.update_drone(
                self.sysid,
                lat=msg.lat / 1e7,
                lon=msg.lon / 1e7,
                alt=msg.relative_alt / 1000.0,
                vx=msg.vx / 100.0,
                vy=msg.vy / 100.0,
                vz=msg.vz / 100.0,
            )

        # --------------------------------------------------
        # BATTERY
        # --------------------------------------------------

        elif msg_type == "SYS_STATUS":

            self.state.update_drone(
                self.sysid,
                battery=msg.battery_remaining,
            )

        # --------------------------------------------------
        # HEADING
        # --------------------------------------------------

        elif msg_type == "VFR_HUD":

            self.state.update_drone(
                self.sysid,
                heading=msg.heading,
            )

        # --------------------------------------------------
        # COMMAND ACK
        # --------------------------------------------------

        elif msg_type == "COMMAND_ACK":

            self.ack_queue.put(msg)

    # ==================================================
    # COMMAND ACK
    # ==================================================

    def wait_for_ack(
        self,
        command,
        timeout=5,
    ):

        start = time.time()

        while time.time() - start < timeout:

            try:

                ack = self.ack_queue.get(
                    timeout=0.2
                )

            except queue.Empty:
                continue

            if ack.command != command:
                continue

            return ack

        return None

    # ==================================================
    # ARM STATE
    # ==================================================

    def wait_until_armed(
        self,
        timeout=10,
    ):

        start = time.time()

        while time.time() - start < timeout:

            state = self.state.get_drone(
                self.sysid
            )

            if state and state.armed:

                return True

            time.sleep(0.2)

        return False

    # ==================================================
    # DISARM STATE
    # ==================================================

    def wait_until_disarmed(
        self,
        timeout=30,
    ):

        start = time.time()

        while time.time() - start < timeout:

            state = self.state.get_drone(
                self.sysid
            )

            if state and not state.armed:

                return True

            time.sleep(0.2)

        return False

    # ==================================================
    # MODE STATE
    # ==================================================

    def wait_for_mode(
        self,
        mode,
        timeout=10,
    ):

        start = time.time()

        while time.time() - start < timeout:

            state = self.state.get_drone(
                self.sysid
            )

            if state and state.mode == mode:

                return True

            time.sleep(0.2)

        return False

    # ==================================================
    # CONNECTION HEALTH
    # ==================================================

    def heartbeat_age(self):

        if self.last_heartbeat == 0:
            return float("inf")

        return time.time() - self.last_heartbeat

    def is_connected(self):

        return self.heartbeat_age() < 3.0

    # ==================================================
    # STATUS
    # ==================================================

    def get_status(self):

        return {
            "sysid": self.sysid,
            "connected": self.is_connected(),
            "heartbeat_age": round(
                self.heartbeat_age(),
                2,
            ),
        }