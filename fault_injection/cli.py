#!/usr/bin/env python3
"""
CLI Tool for Controlled Fault Injection.

Usage:
  python fault_injection/cli.py latency --service payment-service --seconds 3.0 --duration 60
  python fault_injection/cli.py error-spike --service order-service --rate 0.8 --status 500 --duration 60
  python fault_injection/cli.py db-failure --service payment-service --duration 45
  python fault_injection/cli.py list
  python fault_injection/cli.py clear [--service payment-service]
"""

import argparse
import json
import sys
import urllib.request
import urllib.error

SERVICES = {
    "api-gateway": "http://localhost:8000",
    "order-service": "http://localhost:8001",
    "payment-service": "http://localhost:8002",
}


def make_request(url: str, method: str = "GET", data: dict | None = None) -> dict:
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    body = json.dumps(data).encode("utf-8") if data else None
    try:
        with urllib.request.urlopen(req, data=body, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err_msg = exc.read().decode("utf-8")
        try:
            return json.loads(err_msg)
        except Exception:
            return {"error": str(exc), "detail": err_msg}
    except Exception as exc:
        return {"error": f"Failed to connect to {url}: {exc}"}


def cmd_latency(args):
    url = f"{SERVICES[args.service]}/faults/inject"
    payload = {
        "service": args.service,
        "fault_type": "latency",
        "endpoint": args.endpoint,
        "latency_seconds": args.seconds,
        "duration_seconds": args.duration,
    }
    res = make_request(url, method="POST", data=payload)
    print(f"[*] Injected Latency ({args.seconds}s) into {args.service}:")
    print(json.dumps(res, indent=2))


def cmd_error_spike(args):
    url = f"{SERVICES[args.service]}/faults/inject"
    payload = {
        "service": args.service,
        "fault_type": "error_spike",
        "endpoint": args.endpoint,
        "error_rate": args.rate,
        "status_code": args.status,
        "error_message": args.message or "Simulated high error spike",
        "duration_seconds": args.duration,
    }
    res = make_request(url, method="POST", data=payload)
    print(f"[*] Injected Error Spike ({int(args.rate * 100)}% HTTP {args.status}) into {args.service}:")
    print(json.dumps(res, indent=2))


def cmd_db_failure(args):
    url = f"{SERVICES[args.service]}/faults/inject"
    payload = {
        "service": args.service,
        "fault_type": "database_failure",
        "duration_seconds": args.duration,
    }
    res = make_request(url, method="POST", data=payload)
    print(f"[*] Simulated Database Connection Failure on {args.service}:")
    print(json.dumps(res, indent=2))


def cmd_list(args):
    print("=== Active Faults Across Services ===")
    for svc_name, svc_url in SERVICES.items():
        res = make_request(f"{svc_url}/faults/active")
        print(f"\n[{svc_name}]:")
        faults = res.get("active_faults", [])
        if not faults:
            print("  (No active faults)")
        else:
            for f in faults:
                print(f"  - ID: {f.get('fault_id')} | Type: {f.get('fault_type')} | Endpoint: {f.get('endpoint')} | Duration: {f.get('duration_seconds')}s")


def cmd_clear(args):
    target_svcs = [args.service] if args.service else list(SERVICES.keys())
    for svc in target_svcs:
        url = f"{SERVICES[svc]}/faults/clear"
        payload = {"service": svc, "fault_id": args.fault_id}
        res = make_request(url, method="POST", data=payload)
        print(f"[*] Cleared faults on {svc}: {res.get('cleared_count', 0)} cleared")


def main():
    parser = argparse.ArgumentParser(description="AI Incident Response Platform — Fault Injection CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Latency
    p_lat = subparsers.add_parser("latency", help="Inject artificial latency")
    p_lat.add_argument("--service", choices=list(SERVICES.keys()), default="payment-service", help="Target service")
    p_lat.add_argument("--endpoint", default=None, help="Target path prefix")
    p_lat.add_argument("--seconds", type=float, default=2.0, help="Latency in seconds")
    p_lat.add_argument("--duration", type=int, default=60, help="Expiration duration in seconds")
    p_lat.set_defaults(func=cmd_latency)

    # Error spike
    p_err = subparsers.add_parser("error-spike", help="Inject HTTP 5xx error spike")
    p_err.add_argument("--service", choices=list(SERVICES.keys()), default="payment-service", help="Target service")
    p_err.add_argument("--endpoint", default=None, help="Target path prefix")
    p_err.add_argument("--rate", type=float, default=1.0, help="Error rate probability (0.0 to 1.0)")
    p_err.add_argument("--status", type=int, default=500, help="HTTP status code")
    p_err.add_argument("--message", default=None, help="Custom error message")
    p_err.add_argument("--duration", type=int, default=60, help="Expiration duration in seconds")
    p_err.set_defaults(func=cmd_error_spike)

    # DB failure
    p_db = subparsers.add_parser("db-failure", help="Simulate database failure / exhaustion")
    p_db.add_argument("--service", choices=list(SERVICES.keys()), default="payment-service", help="Target service")
    p_db.add_argument("--duration", type=int, default=60, help="Expiration duration in seconds")
    p_db.set_defaults(func=cmd_db_failure)

    # List
    p_list = subparsers.add_parser("list", help="List active faults across services")
    p_list.set_defaults(func=cmd_list)

    # Clear
    p_clr = subparsers.add_parser("clear", help="Clear active faults")
    p_clr.add_argument("--service", choices=list(SERVICES.keys()), default=None, help="Target service or all")
    p_clr.add_argument("--fault-id", default=None, help="Specific fault ID")
    p_clr.set_defaults(func=cmd_clear)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
