#!/usr/bin/env python3
"""Generate one image per prompt per model from public Hugging Face Spaces.

Uses only the public Gradio /gradio_api/call API (no key, no account).
A failed HTTP/queue call may be retried; a successfully returned image is
never regenerated to improve its score. Results are recorded in
results/manifest.csv with a SHA-256 hash for every saved file.
"""
import csv
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = json.loads((ROOT / "data" / "prompts.json").read_text())["prompts"]
CONFIG = json.loads((ROOT / "config.json").read_text())


def gradio_generate(host, data, timeout=150):
    url = f"https://{host}/gradio_api/call/infer"
    req = urllib.request.Request(
        url, data=json.dumps({"data": data}).encode(),
        headers={"Content-Type": "application/json",
                 "User-Agent": "typography-fidelity-study/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        event_id = json.loads(resp.read())["event_id"]
    poll = f"https://{host}/gradio_api/call/infer/{event_id}"
    deadline = time.time() + timeout
    # Silent stretches during generation are longer for the 28-step model
    # than for FLUX's 4 steps; a 30 s read timeout would abandon real SD3.5
    # work, so the poll read timeout scales with the overall cap.
    poll_timeout = 30 if timeout <= 75 else 120
    while time.time() < deadline:
        req = urllib.request.Request(poll, headers={"User-Agent": "typography-fidelity-study/1.0"})
        # Read line by line with a wall-clock deadline check on every line:
        # Gradio holds this stream open while queued, and a stalled queue
        # entry can otherwise keep the connection alive indefinitely (the
        # earlier bug: iterating the stream never returned to the deadline
        # check). A deadline expiry raises, and the caller retries with a
        # fresh event_id; a successfully returned image is never retried.
        with urllib.request.urlopen(req, timeout=poll_timeout) as resp:
            while True:
                if time.time() > deadline:
                    raise TimeoutError(f"no completed result within {timeout}s for event {event_id}")
                raw = resp.readline()
                if not raw:
                    break
                line = raw.decode(errors="ignore").strip()
                if not line.startswith("data:"):
                    continue
                try:
                    payload = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, list):
                    # Newer Gradio: the final SSE data line is the output list.
                    out = payload[0]
                    file_url = out.get("url") if isinstance(out, dict) else None
                    if not file_url:
                        raise RuntimeError(f"no file URL in output: {out!r}")
                    if file_url.startswith("/"):
                        file_url = f"https://{host}" + file_url
                    req2 = urllib.request.Request(file_url, headers={"User-Agent": "typography-fidelity-study/1.0"})
                    with urllib.request.urlopen(req2, timeout=120) as resp2:
                        blob = resp2.read()
                    ext = "png"
                    if isinstance(out, dict) and out.get("orig_name"):
                        ext = out["orig_name"].rsplit(".", 1)[-1].lower()
                    return blob, ext
                if not isinstance(payload, dict):
                    continue
                msg = payload.get("msg")
                if msg == "process_completed":
                    out = payload["output"]["data"][0]
                    file_url = out.get("url") if isinstance(out, dict) else None
                    if not file_url:
                        raise RuntimeError(f"no file URL in output: {out!r}")
                    if file_url.startswith("/"):
                        file_url = f"https://{host}" + file_url
                    req2 = urllib.request.Request(file_url, headers={"User-Agent": "typography-fidelity-study/1.0"})
                    with urllib.request.urlopen(req2, timeout=120) as resp2:
                        blob = resp2.read()
                    ext = "png"
                    if isinstance(out, dict) and out.get("orig_name"):
                        ext = out["orig_name"].rsplit(".", 1)[-1].lower()
                    return blob, ext
                if msg in ("process_failed", "error"):
                    raise RuntimeError(f"space reported {msg}: {payload}")
        time.sleep(5)
    raise TimeoutError(f"no completed result within {timeout}s for event {event_id}")


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    images_dir = ROOT / "images"
    images_dir.mkdir(exist_ok=True)
    manifest_path = ROOT / "results" / "manifest.csv"
    manifest_path.parent.mkdir(exist_ok=True)
    existing = {}
    if manifest_path.exists():
        with manifest_path.open() as fh:
            for row in csv.DictReader(fh):
                existing[(row["model"], row["prompt_id"])] = row
    rows = list(existing.values())
    for model in CONFIG["models"]:
        if only and model["short"] != only:
            continue
        for item in PROMPTS:
            key = (model["short"], item["id"])
            if key in existing:
                continue
            params = model["params"]
            width, height = CONFIG["image_size"]
            if model["short"] == "flux-schnell":
                data = [item["prompt"], params["seed"], False, width, height,
                        params["num_inference_steps"]]
            else:
                data = [item["prompt"], params["negative_prompt"], params["seed"],
                        False, width, height, params["guidance_scale"],
                        params["num_inference_steps"]]
            attempts = 0
            while True:
                attempts += 1
                try:
                    # FLUX.1-schnell at 4 steps completes in under 10 s when
                    # the Space queue is free; a stalled queue entry never
                    # recovered within 150 s in testing, so a 75 s cap for
                    # FLUX retries sooner without abandoning real work.
                    # SD3.5 Medium (40 steps) keeps a longer cap.
                    cap = 75 if model["short"] == "flux-schnell" else (
                        300 if model["short"] == "sd35-medium" else 180)
                    blob, ext = gradio_generate(model["space_host"], data, timeout=cap)
                    break
                except Exception as exc:  # noqa: BLE001 - retry transient queue failures
                    print(f"RETRY {key} attempt {attempts}: {exc}", flush=True)
                    if attempts >= 3:
                        raise
                    time.sleep(20)
            out_path = images_dir / f"{model['short']}_{item['id']}.{ext}"
            out_path.write_bytes(blob)
            rows.append({
                "model": model["short"], "model_display": model["display"],
                "space_id": model["space_id"], "prompt_id": item["id"],
                "category": item["category"], "prompt": item["prompt"],
                "seed": params["seed"], "width": width, "height": height,
                "params": json.dumps(params, sort_keys=True),
                "file": out_path.name, "bytes": len(blob),
                "sha256": hashlib.sha256(blob).hexdigest(),
                "attempts": attempts,
                "generated_at_kabul": time.strftime("%Y-%m-%d %H:%M %Z"),
            })
            with manifest_path.open("w", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
            print(f"DONE {key} -> {out_path.name} ({len(blob)} bytes)", flush=True)


if __name__ == "__main__":
    main()
