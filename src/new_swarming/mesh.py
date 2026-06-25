



import json
import queue
import socket
import threading
import time

from typing import Dict, Any

from loguru import logger


class MeshNode:

    BASE_PORT = 15000

    def __init__(
        self,
        sysid: int,
        mavlink_port: int,
        peer_sysids: list[int],
    ):

        self.sysid = sysid

        self.port = (
            self.BASE_PORT + sysid
        )

        self.peers = [

            self.BASE_PORT + peer

            for peer in peer_sysids

            if peer != sysid
        ]

        self.sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
        )

        self.sock.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1,
        )

        self.sock.settimeout(
            1.0
        )

        self.sock.bind(
            ("127.0.0.1", self.port)
        )

        self.running = False

        self.lock = threading.Lock()

        self.last_seen: Dict[
            int,
            float,
        ] = {}

        self.inbox = queue.Queue(
            maxsize=1000
        )

        self.rx_thread = None
        self.hb_thread = None

    # ==================================================
    # START
    # ==================================================

    def start(self):

        if self.running:
            return

        self.running = True

        self.rx_thread = threading.Thread(
            target=self._rx_loop,
            daemon=True,
        )

        self.hb_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
        )

        self.rx_thread.start()
        self.hb_thread.start()

        logger.success(
            f"[MESH {self.sysid}] ACTIVE "
            f"PORT={self.port}"
        )

    # ==================================================
    # RX
    # ==================================================

    def _rx_loop(self):

        while self.running:

            try:

                data, _ = self.sock.recvfrom(
                    4096
                )

                msg = json.loads(
                    data.decode()
                )

                if not isinstance(
                    msg,
                    dict,
                ):
                    continue

                sender = msg.get(
                    "from"
                )

                if sender is not None:

                    with self.lock:

                        self.last_seen[
                            sender
                        ] = time.time()

                try:

                    self.inbox.put_nowait(
                        msg
                    )

                except queue.Full:

                    logger.warning(
                        f"[MESH {self.sysid}] "
                        f"Inbox full"
                    )

            except socket.timeout:

                continue

            except OSError:

                break

            except Exception as e:

                logger.debug(
                    f"[MESH {self.sysid}] "
                    f"RX error: {e}"
                )

    # ==================================================
    # HEARTBEAT
    # ==================================================

    def _heartbeat_loop(self):

        while self.running:

            try:

                self.broadcast(
                    "HELLO",
                    {
                        "sysid": self.sysid,
                    },
                )

                self._cleanup_peers()

                time.sleep(1)

            except Exception as e:

                logger.debug(
                    f"[MESH {self.sysid}] "
                    f"HB error: {e}"
                )

    # ==================================================
    # PEER CLEANUP
    # ==================================================

    def _cleanup_peers(self):

        now = time.time()

        with self.lock:

            stale = [

                peer

                for peer, ts
                in self.last_seen.items()

                if now - ts > 5
            ]

            for peer in stale:

                self.last_seen.pop(
                    peer,
                    None,
                )

    # ==================================================
    # SEND
    # ==================================================

    def broadcast(
        self,
        msg_type: str,
        data: Dict[str, Any],
    ):

        payload = {

            "from": self.sysid,

            "type": msg_type,

            "timestamp": time.time(),

            "data": data,
        }

        encoded = json.dumps(
            payload
        ).encode()

        for peer_port in self.peers:

            try:

                self.sock.sendto(
                    encoded,
                    (
                        "127.0.0.1",
                        peer_port,
                    ),
                )

            except Exception:

                pass

    # ==================================================
    # READ
    # ==================================================

    def read_all(self):

        messages = []

        while True:

            try:

                messages.append(
                    self.inbox.get_nowait()
                )

            except queue.Empty:

                break

        return messages

    # ==================================================
    # PEERS
    # ==================================================

    def peer_count(self):

        with self.lock:

            return len(
                self.last_seen
            )

    def peer_list(self):

        with self.lock:

            return list(
                self.last_seen.keys()
            )

    # ==================================================
    # STOP
    # ==================================================

    def stop(self):

        self.running = False

        try:

            self.sock.close()

        except Exception:

            pass

        if self.rx_thread:

            self.rx_thread.join(
                timeout=2
            )

        if self.hb_thread:

            self.hb_thread.join(
                timeout=2
            )

        logger.info(
            f"[MESH {self.sysid}] Stopped"
        )