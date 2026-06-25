


from loguru import logger
from pymavlink import mavutil


DEFAULT_PORTS = [
    14550,
    14560,
    14570,
]


def discover_drones(
    ports=None,
    heartbeat_timeout=10,
):

    if ports is None:
        ports = DEFAULT_PORTS

    drones = []
    discovered_sysids = set()

    logger.info(
        f"[DISCOVERY] Scanning {len(ports)} ports"
    )

    for port in ports:

        master = None

        try:

            endpoint = (
                f"udpin:0.0.0.0:{port}"
            )

            logger.info(
                f"[DISCOVERY] Connecting -> {endpoint}"
            )

            master = mavutil.mavlink_connection(
                endpoint
            )

            hb = master.wait_heartbeat(
                timeout=heartbeat_timeout
            )

            if hb is None:

                logger.warning(
                    f"[DISCOVERY] No heartbeat on {port}"
                )

                master.close()
                continue

            sysid = hb.get_srcSystem()
            compid = hb.get_srcComponent()

            if sysid in discovered_sysids:

                logger.warning(
                    f"[DISCOVERY] Duplicate SYSID "
                    f"{sysid}"
                )

                master.close()
                continue

            discovered_sysids.add(sysid)

            try:

                master.mav.request_data_stream_send(
                    sysid,
                    compid,
                    mavutil.mavlink.MAV_DATA_STREAM_ALL,
                    10,
                    1,
                )

            except Exception as e:

                logger.debug(
                    f"[DISCOVERY] Stream request failed: {e}"
                )

            logger.success(
                f"[DISCOVERY] FOUND "
                f"SYSID={sysid} "
                f"COMPID={compid} "
                f"PORT={port}"
            )

            drones.append(
                {
                    "sysid": sysid,
                    "compid": compid,
                    "port": port,
                    "master": master,
                }
            )

        except Exception as e:

            logger.warning(
                f"[DISCOVERY] Port {port} failed: {e}"
            )

            if master is not None:

                try:
                    master.close()
                except Exception:
                    pass

    logger.success(
        f"[DISCOVERY] "
        f"{len(drones)} drone(s) discovered"
    )

    return drones