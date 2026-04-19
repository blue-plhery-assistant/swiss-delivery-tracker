"""CLI entry point for Swiss Delivery Tracker."""

import argparse
import sys

from . import __version__
from .tracker import (
    load_deliveries,
    save_deliveries,
    add_delivery,
    update_all,
    update_delivery,
    remove_delivery,
    DEFAULT_DATA_FILE,
)
from .models import normalize_carrier, CARRIER_ALIASES


STATUS_ICONS = {
    "pending": "⏳",
    "in_transit": "🚚",
    "out_for_delivery": "📬",
    "delivered": "✅",
    "exception": "⚠️",
    "removed": "🗑️",
    "unknown": "❓",
}


def format_table(deliveries):
    """Format deliveries as a simple aligned table."""
    if not deliveries:
        print("No deliveries found.")
        return

    # Calculate column widths
    rows = []
    for d in deliveries:
        icon = STATUS_ICONS.get(d.get("status", ""), "❓")
        rows.append([
            icon,
            d.get("tracking_number", "-")[:24],
            d.get("carrier", "")[:20],
            d.get("description", "")[:35],
            d.get("status", "")[:16],
            d.get("expected_delivery", "-") or "-",
        ])

    headers = ["", "Tracking", "Carrier", "Description", "Status", "ETA"]
    widths = [max(len(str(r[i])) for r in [headers] + rows) for i in range(len(headers))]

    # Print header
    header_line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    print(header_line)
    print("-" * len(header_line))

    # Print rows
    for row in rows:
        print("  ".join(str(col).ljust(widths[i]) for i, col in enumerate(row)))


def format_detail(d):
    """Print detailed view of a single delivery."""
    icon = STATUS_ICONS.get(d.get("status", ""), "❓")
    print(f"\n{icon} {d.get('description', 'Unknown package')}")
    print(f"{'='*60}")
    print(f"  Tracking:   {d.get('tracking_number', '-')}")
    print(f"  Carrier:    {d.get('carrier', '-')}")
    print(f"  Status:     {d.get('status', '-')} - {d.get('last_status_text', '')}")
    print(f"  Last update: {d.get('last_update', '-')}")
    print(f"  ETA:        {d.get('expected_delivery', '-') or '-'}")
    if d.get("origin"):
        print(f"  Route:      {d['origin']} -> {d.get('destination', 'CH')}")
    if d.get("notes"):
        print(f"  Notes:      {d['notes']}")

    events = d.get("events") or []
    if events:
        print(f"\n  Events ({len(events)}):")
        for e in events[:15]:
            loc = f" [{e['location']}]" if e.get("location") else ""
            print(f"    {e.get('time', '')}{loc}")
            print(f"      {e.get('description', '')}")
    print()


def cmd_add(args):
    deliveries = load_deliveries(args.data_file)
    carrier = normalize_carrier(args.carrier)
    entry = add_delivery(
        deliveries,
        tracking_number=args.tracking,
        carrier=carrier,
        description=args.description,
        source=args.source,
        origin=args.origin,
        notes=args.notes,
    )
    save_deliveries(deliveries, args.data_file)
    print(f"Added delivery #{entry['id']}: {args.description} ({args.tracking or 'no tracking yet'})")

    if args.tracking and not args.no_update:
        print("Fetching initial status...")
        if update_delivery(entry):
            save_deliveries(deliveries, args.data_file)
            print(f"  Status: {entry.get('status')} - {entry.get('last_status_text', '')}")


def cmd_update(args):
    deliveries = load_deliveries(args.data_file)
    if not deliveries:
        print("No deliveries to update.")
        return

    updated, errors = update_all(deliveries, include_delivered=args.all)
    save_deliveries(deliveries, args.data_file)
    print(f"\nDone. Updated {updated} deliveries ({errors} skipped/errored).")


def cmd_list(args):
    deliveries = load_deliveries(args.data_file)
    if not deliveries:
        print("No deliveries found. Add one with: swiss-delivery-tracker add")
        return

    status_filter = args.status.lower() if args.status else "active"

    if status_filter == "all":
        filtered = [d for d in deliveries if d.get("status") != "removed"]
    elif status_filter == "active":
        filtered = [d for d in deliveries if d.get("status") not in ("delivered", "removed")]
    elif status_filter == "delivered":
        filtered = [d for d in deliveries if d.get("status") == "delivered"]
    else:
        filtered = [d for d in deliveries if d.get("status") == status_filter]

    if not filtered:
        print(f"No deliveries with status '{status_filter}'.")
        return

    format_table(filtered)


def cmd_show(args):
    deliveries = load_deliveries(args.data_file)
    target = args.tracking

    found = None
    for d in deliveries:
        if d.get("tracking_number") == target or d.get("id") == target:
            found = d
            break

    if not found:
        print(f"Delivery not found: {target}")
        sys.exit(1)

    format_detail(found)


def cmd_remove(args):
    deliveries = load_deliveries(args.data_file)
    removed = remove_delivery(deliveries, args.tracking)
    if removed:
        save_deliveries(deliveries, args.data_file)
        print(f"Removed: {removed.get('description', '')} ({args.tracking})")
    else:
        print(f"Delivery not found: {args.tracking}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="swiss-delivery-tracker",
        description="Track package deliveries in Switzerland",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--data-file",
        default=None,
        help=f"Path to deliveries JSON file (default: {DEFAULT_DATA_FILE})",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # add
    p_add = subparsers.add_parser("add", help="Add a new delivery")
    p_add.add_argument("--tracking", "-t", default=None, help="Tracking number")
    p_add.add_argument("--carrier", "-c", required=True, help="Carrier name")
    p_add.add_argument("--description", "-d", required=True, help="Package description")
    p_add.add_argument("--source", "-s", default=None, help="Shop/source name")
    p_add.add_argument("--origin", default=None, help="Origin country code (e.g. CN, DE)")
    p_add.add_argument("--notes", default=None, help="Optional notes")
    p_add.add_argument("--no-update", action="store_true", help="Don't fetch status after adding")

    # update
    p_update = subparsers.add_parser("update", help="Update all active deliveries")
    p_update.add_argument("--all", "-a", action="store_true", help="Also update delivered packages")

    # list
    p_list = subparsers.add_parser("list", help="List deliveries")
    p_list.add_argument(
        "--status", "-s",
        default="active",
        help="Filter: active (default), delivered, all, or any status name",
    )

    # show
    p_show = subparsers.add_parser("show", help="Show delivery details")
    p_show.add_argument("tracking", help="Tracking number or delivery ID")

    # remove
    p_remove = subparsers.add_parser("remove", help="Remove a delivery")
    p_remove.add_argument("tracking", help="Tracking number or delivery ID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "add": cmd_add,
        "update": cmd_update,
        "list": cmd_list,
        "show": cmd_show,
        "remove": cmd_remove,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
