

from loguru import logger


class Swarm:

    def __init__(
        self,
        drones,
        state_store,
    ):

        self.drones = drones
        self.state = state_store

        if drones:

            self.state.swarm_state.leader_id = (
                drones[0].sysid
            )

            self.state.swarm_state.mode = (
                "INITIALIZED"
            )

        else:

            self.state.swarm_state.mode = (
                "EMPTY"
            )

    # ==================================================
    # TAKEOFF ALL
    # ==================================================

    def takeoff_all(
        self,
        altitude=5.0,
    ):

        if not self.drones:

            logger.warning(
                "[SWARM] No drones available"
            )

            return []

        logger.info(
            f"[SWARM] TAKEOFF ALL "
            f"({len(self.drones)} drones)"
        )

        self.state.swarm_state.mode = (
            "TAKEOFF"
        )

        results = []

        with ThreadPoolExecutor(
            max_workers=len(self.drones)
        ) as executor:

            futures = {

                executor.submit(
                    drone.takeoff,
                    altitude,
                ): drone

                for drone in self.drones
            }

            for future in as_completed(
                futures
            ):

                drone = futures[future]

                try:

                    result = future.result()

                    logger.info(
                        f"[SWARM] SYSID={drone.sysid} "
                        f"takeoff={result}"
                    )

                    results.append(result)

                except Exception as e:

                    logger.error(
                        f"[SWARM] SYSID={drone.sysid} "
                        f"takeoff exception: {e}"
                    )

                    results.append(False)

        success_count = sum(results)

        logger.info(
            f"[SWARM] TAKEOFF RESULT "
            f"{success_count}/{len(self.drones)}"
        )

        if success_count == len(self.drones):

            self.state.swarm_state.mode = (
                "AIRBORNE"
            )

        elif success_count > 0:

            self.state.swarm_state.mode = (
                "PARTIAL_AIRBORNE"
            )

        else:

            self.state.swarm_state.mode = (
                "TAKEOFF_FAILED"
            )

        return results

    # ==================================================
    # LAND ALL
    # ==================================================

    def land_all(self):

        if not self.drones:

            logger.warning(
                "[SWARM] No drones available"
            )

            return []

        logger.info(
            "[SWARM] LAND ALL"
        )

        self.state.swarm_state.mode = (
            "LANDING"
        )

        results = []

        with ThreadPoolExecutor(
            max_workers=len(self.drones)
        ) as executor:

            futures = {

                executor.submit(
                    drone.land
                ): drone

                for drone in self.drones
            }

            for future in as_completed(
                futures
            ):

                drone = futures[future]

                try:

                    result = future.result()

                    logger.info(
                        f"[SWARM] SYSID={drone.sysid} "
                        f"land={result}"
                    )

                    results.append(result)

                except Exception as e:

                    logger.error(
                        f"[SWARM] SYSID={drone.sysid} "
                        f"land exception: {e}"
                    )

                    results.append(False)

        success_count = sum(results)

        logger.info(
            f"[SWARM] LAND RESULT "
            f"{success_count}/{len(self.drones)}"
        )

        if success_count == len(self.drones):

            self.state.swarm_state.mode = (
                "LANDED"
            )

        elif success_count > 0:

            self.state.swarm_state.mode = (
                "PARTIAL_LANDED"
            )

        else:

            self.state.swarm_state.mode = (
                "LAND_FAILED"
            )

        return results

    # ==================================================
    # EMERGENCY LAND
    # ==================================================

    def emergency_land(self):

        logger.warning(
            "[SWARM] EMERGENCY LAND"
        )

        return self.land_all()

    # ==================================================
    # FIND DRONE
    # ==================================================

    def get_drone(
        self,
        sysid,
    ):

        for drone in self.drones:

            if drone.sysid == sysid:
                return drone

        return None

    # ==================================================
    # SWARM SNAPSHOT
    # ==================================================

    def snapshot(self):

        data = []

        for drone in self.drones:

            try:

                data.append(
                    drone.snapshot()
                )

            except Exception:

                data.append(
                    {
                        "sysid": drone.sysid,
                        "mode": "ERROR",
                        "armed": False,
                        "alt": 0.0,
                        "battery": 0,
                        "heading": 0.0,
                    }
                )

        return sorted(
            data,
            key=lambda x: x["sysid"]
        )

    # ==================================================
    # SWARM STATUS
    # ==================================================

    def status(self):

        return {
            "leader_id":
                self.state.swarm_state.leader_id,

            "mode":
                self.state.swarm_state.mode,

            "drone_count":
                len(self.drones),

            "connected":
                self.connected_count(),
        }

    # ==================================================
    # CONNECTED COUNT
    # ==================================================

    def connected_count(self):

        count = 0

        for drone in self.drones:

            if drone.mavlink.is_connected():

                count += 1

        return count

    # ==================================================
    # ELECT LEADER
    # ==================================================

    def elect_leader(self):

        connected = [

            drone

            for drone in self.drones

            if drone.mavlink.is_connected()
        ]

        if not connected:

            logger.warning(
                "[SWARM] No connected drones"
            )

            self.state.swarm_state.leader_id = None

            return None

        leader = min(
            connected,
            key=lambda d: d.sysid,
        )

        self.state.swarm_state.leader_id = (
            leader.sysid
        )

        logger.info(
            f"[SWARM] New leader "
            f"SYSID={leader.sysid}"
        )

        return leader.sysid

    # ==================================================
    # HEALTH REPORT
    # ==================================================

    def health_report(self):

        report = []

        for drone in self.drones:

            report.append(
                {
                    "sysid": drone.sysid,
                    "connected":
                        drone.mavlink.is_connected(),

                    "heartbeat_age":
                        round(
                            drone.mavlink.heartbeat_age(),
                            2,
                        ),
                }
            )

        return report

    # ==================================================
    # SHUTDOWN
    # ==================================================

    def shutdown(self):

        logger.info(
            "[SWARM] Shutdown initiated"
        )

        for drone in self.drones:

            try:

                drone.stop()

            except Exception as e:

                logger.error(
                    f"[SWARM] Failed stopping "
                    f"SYSID={drone.sysid}: {e}"
                )

        self.state.swarm_state.mode = (
            "SHUTDOWN"
        )

        logger.success(
            "[SWARM] Shutdown complete"
        )