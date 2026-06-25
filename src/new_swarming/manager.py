from loguru import logger


class DroneManager:

    def __init__(self):

        self.drones = {}

    # ==================================================
    # ADD
    # ==================================================

    def add(self, drone):

        self.drones[drone.sysid] = drone

        logger.info(
            f"Registered drone SYSID={drone.sysid}"
        )

    # ==================================================
    # REMOVE
    # ==================================================

    def remove(self, sysid):

        drone = self.drones.pop(
            sysid,
            None,
        )

        if drone:

            logger.warning(
                f"Removed drone SYSID={sysid}"
            )

        return drone

    # ==================================================
    # GET
    # ==================================================

    def get(self, sysid):

        return self.drones.get(sysid)

    # ==================================================
    # LIST
    # ==================================================

    def list_drones(self):

        return list(
            self.drones.values()
        )

    # ==================================================
    # COUNT
    # ==================================================

    def count(self):

        return len(
            self.drones
        )

    # ==================================================
    # CONNECTED
    # ==================================================

    def connected_drones(self):

        return [

            drone

            for drone in self.drones.values()

            if drone.mavlink.is_connected()

        ]

    # ==================================================
    # HEALTH
    # ==================================================

    def health(self):

        total = len(
            self.drones
        )

        connected = sum(

            drone.mavlink.is_connected()

            for drone in self.drones.values()

        )

        return {
            "total": total,
            "connected": connected,
            "offline": total - connected,
        }

    # ==================================================
    # LOWEST SYSID
    # ==================================================

    def lowest_sysid(self):

        if not self.drones:
            return None

        return min(
            self.drones.keys()
        )