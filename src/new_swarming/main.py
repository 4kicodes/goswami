






import threading
import time

from loguru import logger

from .discovery import discover_drones
from .drone import Drone
from .swarm import Swarm
from .manager import DroneManager
from .state import StateStore
from .ui import run_dashboard
from .ui import banner


def wait_for_connections(
    drones,
    timeout=10,
):

    logger.info(
        "[SYSTEM] Waiting for MAVLink telemetry..."
    )

    start = time.time()

    while time.time() - start < timeout:

        connected = sum(
            drone.mavlink.is_connected()
            for drone in drones
        )

        if connected == len(drones):

            logger.success(
                f"[SYSTEM] "
                f"All {connected} drones connected"
            )

            return True

        time.sleep(0.5)

    logger.warning(
        "[SYSTEM] Connection timeout"
    )

    return False


def main():

    banner()

    state_store = StateStore()

    manager = DroneManager()

    swarm = None

    try:

        # ==========================================
        # DISCOVERY
        # ==========================================

        discovered = discover_drones()

        if not discovered:

            logger.error(
                "[SYSTEM] No drones discovered"
            )

            return

        drones = []

        for d in discovered:

            drone = Drone(
                d["sysid"],
                d["compid"],
                d["port"],
                d["master"],
                state_store,
            )

            manager.add(drone)

            drones.append(drone)

        logger.success(
            f"[SYSTEM] "
            f"{len(drones)} drones initialized"
        )

        # ==========================================
        # START MAVLINK
        # ==========================================

        for drone in drones:

            drone.start()

        # ==========================================
        # WAIT FOR HEARTBEATS
        # ==========================================

        wait_for_connections(
            drones,
            timeout=10,
        )

        # ==========================================
        # START MESH
        # ==========================================

        sysids = [

            drone.sysid

            for drone in drones
        ]

        for drone in drones:

            drone.enable_mesh(
                sysids
            )

        # ==========================================
        # CREATE SWARM
        # ==========================================

        swarm = Swarm(
            drones,
            state_store,
        )

        logger.success(
            "[SYSTEM] Swarm ready"
        )

        # ==========================================
        # OPTIONAL AUTO TAKEOFF
        # ==========================================

        # ==========================================
# AUTO TAKEOFF
# ==========================================

        AUTO_TAKEOFF = True

        if AUTO_TAKEOFF:

            logger.info(
            "[SYSTEM] Starting takeoff sequence"
        )

            threading.Thread(
                target=swarm.takeoff_all,
                args=(5,),
                daemon=True,
            ).start()
        # ==========================================
        # DASHBOARD
        # ==========================================

        run_dashboard(
            state_store,
            swarm,
        )

    except KeyboardInterrupt:

        logger.warning(
            "[SYSTEM] CTRL+C detected"
        )

    except Exception as e:

        logger.exception(
            f"[SYSTEM] Fatal error: {e}"
        )

    finally:

        if swarm:

            swarm.shutdown()

        logger.success(
            "[SYSTEM] Clean shutdown complete"
        )


if __name__ == "__main__":
    main()