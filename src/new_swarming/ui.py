

import time
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.console import Console

console = Console()


# ==================================================
# BANNER (FIXED)
# ==================================================

def banner():
    panel = Panel(
        "[bold cyan]SWARM CONTROL SYSTEM[/bold cyan]\n"
        "[white]Multi-Drone SITL Swarm Framework[/white]",
        border_style="cyan"
    )

    console.print(panel)
    console.print()


# ==================================================
# SAFE FORMATTERS
# ==================================================

def safe(v, default="--"):
    return default if v is None else str(v)


def fmt_alt(v):
    return "--" if v is None else f"{float(v):5.1f} m"


def fmt_bat(v):
    return "--" if v is None else f"{int(v):3d}%"


def fmt_bool(v):
    return "✓" if v else "✗"


def fmt_heading(v):
    return "--" if v is None else f"{int(v):3d}°"


# ==================================================
# HEADER
# ==================================================

def header():
    return Panel(
        "[bold cyan]SWARM CONTROL DASHBOARD[/bold cyan]\n"
        "[white]Real-time Multi-Drone Telemetry[/white]",
        border_style="cyan",
    )


# ==================================================
# TABLE (STABLE + NO COLLAPSE)
# ==================================================

def build_table(snapshot, swarm_state):

    table = Table(
        title="#### ---- SWARM STATE ---- ####",
        expand=True,
        show_lines=False,
        pad_edge=False,
    )

    table.add_column("SYS", width=6, justify="center")
    table.add_column("MODE", width=10, justify="center")
    table.add_column("ARM", width=5, justify="center")
    table.add_column("ALT", width=10, justify="center")
    table.add_column("BAT", width=6, justify="center")
    table.add_column("HDG", width=6, justify="center")

    for d in snapshot:

        sysid = d.get("sysid", "?")
        mode = d.get("mode", "--")

        is_leader = getattr(swarm_state, "leader_id", None) == sysid
        leader = "(Leader)" if is_leader else ""

        table.add_row(
            f"{sysid}{leader}",
            safe(mode),
            fmt_bool(d.get("armed")),
            fmt_alt(d.get("alt")),
            fmt_bat(d.get("battery")),
            fmt_heading(d.get("heading")),
        )

    return table


# ==================================================
# INFO PANEL
# ==================================================

def build_info_panel(swarm_state, count):

    leader = getattr(swarm_state, "leader_id", "--")
    mode = getattr(swarm_state, "mode", "--")

    return Panel(
        f"[bold]Leader:[/bold] {leader}\n"
        f"[bold]Drones:[/bold] {count}\n"
        f"[bold]Swarm Mode:[/bold] {mode}",
        border_style="green",
    )


# ==================================================
# ROOT LAYOUT
# ==================================================

def render(snapshot, swarm_state, count):

    layout = Layout()

    layout.split_column(
        Layout(header(), size=4),
        Layout(name="body"),
        Layout(name="footer", size=6),
    )

    layout["body"].update(build_table(snapshot, swarm_state))
    layout["footer"].update(build_info_panel(swarm_state, count))

    return layout


# ==================================================
# LIVE DASHBOARD LOOP (STABLE)
# ==================================================

def run_dashboard(state_store, swarm, refresh_rate=5):

    with Live(
        render([], state_store.swarm_state, len(swarm.drones)),
        refresh_per_second=refresh_rate,
        screen=True,
    ) as live:

        while True:
            try:
                drones_state, _, swarm_state = state_store.get_snapshot()

                snapshot = swarm.snapshot()

                live.update(
                    render(snapshot, swarm_state, len(swarm.drones))
                )

                time.sleep(0.2)

            except Exception as e:
                live.update(
                    Panel(f"[red]UI ERROR: {e}[/red]")
                )
                time.sleep(1)