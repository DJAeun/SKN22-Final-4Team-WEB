#!/usr/bin/env python
"""
run_lora_workflow.py
────────────────────
Runs '하리_로라먹인 (1).json' 300 times against ComfyUI.
Each run gets a random seed and resolves {option1|option2} wildcards in the prompt.

Usage:
    python run_lora_workflow.py
"""

import json
import os
import random
import re
import time

import requests
import websocket  # pip install websocket-client

# ── Config ────────────────────────────────────────────────────────────────────

COMFYUI_URL = "https://pflzfv2syqnjy4-8188.proxy.runpod.net"
WORKFLOW_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "하리_로라먹인 (1).json")
SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_images", "hari_studio")
NUM_IMAGES = 300

# Node IDs inside the workflow
NODE_KSAMPLER  = "70"   # KSampler — seed lives here
NODE_CLIP_TEXT = "67"   # CLIPTextEncode — prompt with wildcards

# ── Wildcard resolver ─────────────────────────────────────────────────────────

def resolve_wildcards(text: str) -> str:
    """Recursively resolve {option1|option2|...} groups by random choice."""
    pattern = re.compile(r"\{([^{}]+)\}")
    while pattern.search(text):
        text = pattern.sub(
            lambda m: random.choice(m.group(1).split("|")).strip(),
            text,
        )
    return text

# ── Build API prompt from workflow JSON ───────────────────────────────────────

def load_workflow() -> dict:
    with open(WORKFLOW_PATH, encoding="utf-8") as f:
        return json.load(f)

def build_api_prompt(workflow: dict, seed: int) -> dict:
    """
    Convert the ComfyUI GUI workflow format into the API prompt format.
    Only NODE_KSAMPLER (seed) and NODE_CLIP_TEXT (wildcards) are modified per run.
    All other nodes are passed through as-is from the workflow.
    """
    nodes = {node["id"]: node for node in workflow["nodes"]}

    api: dict = {}

    for node_id, node in nodes.items():
        ntype = node["type"]

        # Skip UI-only nodes
        if ntype in ("MarkdownNote", "Note", "PrimitiveNode"):
            continue

        inputs = {}

        # Resolve input links → reference other node outputs
        for inp in node.get("inputs", []):
            link_id = inp.get("link")
            if link_id is None:
                continue
            # Find the source node/slot for this link
            for link in workflow.get("links", []):
                # link format: [link_id, src_node_id, src_slot, dst_node_id, dst_slot, type]
                if link[0] == link_id:
                    src_node_id = str(link[1])
                    src_slot    = link[2]
                    inputs[inp["name"]] = [src_node_id, src_slot]
                    break

        # Fill widget values
        widgets = node.get("widgets_values", [])
        widget_idx = 0

        if ntype == "VAELoader":
            inputs["vae_name"] = widgets[0] if widgets else "ae.safetensors"

        elif ntype == "UNETLoader":
            inputs["unet_name"]    = widgets[0] if len(widgets) > 0 else ""
            inputs["weight_dtype"] = widgets[1] if len(widgets) > 1 else "default"

        elif ntype == "CLIPLoader":
            inputs["clip_name"] = widgets[0] if len(widgets) > 0 else ""
            inputs["type"]      = widgets[1] if len(widgets) > 1 else "lumina2"
            inputs["device"]    = widgets[2] if len(widgets) > 2 else "default"

        elif ntype == "LoraLoader":
            inputs["lora_name"]      = widgets[0] if len(widgets) > 0 else ""
            inputs["strength_model"] = widgets[1] if len(widgets) > 1 else 1
            inputs["strength_clip"]  = widgets[2] if len(widgets) > 2 else 1

        elif ntype == "CLIPTextEncode":
            raw_text = widgets[0] if widgets else ""
            inputs["text"] = resolve_wildcards(raw_text)

        elif ntype == "ConditioningZeroOut":
            pass  # no widget values, only the linked conditioning input

        elif ntype == "EmptySD3LatentImage":
            inputs["width"]      = widgets[0] if len(widgets) > 0 else 1024
            inputs["height"]     = widgets[1] if len(widgets) > 1 else 1024
            inputs["batch_size"] = widgets[2] if len(widgets) > 2 else 1

        elif ntype == "ModelSamplingAuraFlow":
            inputs["shift"] = widgets[0] if widgets else 3

        elif ntype == "KSampler":
            # widgets: [seed, control_after_generate, steps, cfg, sampler, scheduler, denoise]
            inputs["seed"]         = seed
            inputs["steps"]        = widgets[2] if len(widgets) > 2 else 8
            inputs["cfg"]          = widgets[3] if len(widgets) > 3 else 1
            inputs["sampler_name"] = widgets[4] if len(widgets) > 4 else "res_multistep"
            inputs["scheduler"]    = widgets[5] if len(widgets) > 5 else "simple"
            inputs["denoise"]      = widgets[6] if len(widgets) > 6 else 1

        elif ntype == "VAEDecode":
            pass  # inputs come from links only

        elif ntype == "SaveImage":
            inputs["filename_prefix"] = str(seed)

        else:
            # Unknown node — pass widgets as positional (best-effort)
            pass

        api[str(node_id)] = {
            "class_type": ntype,
            "inputs": inputs,
        }

    return api

# ── ComfyUI API helpers ───────────────────────────────────────────────────────

def queue_prompt(api_prompt: dict, client_id: str) -> dict:
    payload  = {"prompt": api_prompt, "client_id": client_id}
    response = requests.post(f"{COMFYUI_URL}/prompt", json=payload, timeout=30)
    response.raise_for_status()
    return response.json()

def get_history(prompt_id: str) -> dict:
    response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=15)
    response.raise_for_status()
    return response.json()

def get_image(filename: str, subfolder: str, folder_type: str) -> bytes:
    params   = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    response = requests.get(f"{COMFYUI_URL}/view", params=params, timeout=60)
    response.raise_for_status()
    return response.content

def wait_for_completion(ws: websocket.WebSocket, prompt_id: str) -> bool:
    """Block until the queued prompt finishes. Returns True on success."""
    while True:
        raw = ws.recv()
        if not isinstance(raw, str):
            continue  # skip binary preview frames
        msg      = json.loads(raw)
        msg_type = msg.get("type", "")
        data     = msg.get("data", {})

        if msg_type == "executing":
            if data.get("prompt_id") == prompt_id and data.get("node") is None:
                return True  # execution complete

        elif msg_type == "progress":
            v = data.get("value", 0)
            m = data.get("max", 1)
            print(f"  step {v}/{m}", end="\r")

        elif msg_type == "execution_error":
            if data.get("prompt_id") == prompt_id:
                print(f"\n  ERROR: {data.get('exception_message', 'unknown error')}")
                return False

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(SAVE_DIR, exist_ok=True)

    print("=" * 60)
    print(f"  Workflow : 하리_로라먹인 (1).json")
    print(f"  Target   : {NUM_IMAGES} images")
    print(f"  ComfyUI  : {COMFYUI_URL}")
    print(f"  Save dir : {SAVE_DIR}")
    print("=" * 60)

    # Verify ComfyUI is reachable
    try:
        resp = requests.get(f"{COMFYUI_URL}/system_stats", timeout=10)
        resp.raise_for_status()
        print("ComfyUI: online\n")
    except Exception as e:
        print(f"ERROR: Cannot reach ComfyUI at {COMFYUI_URL}\n  {e}")
        return

    # Load workflow once
    workflow   = load_workflow()
    client_id  = f"lora_{random.randint(0, 999999):06d}"

    # WebSocket connection
    ws_url = COMFYUI_URL.rstrip("/").replace("https://", "wss://").replace("http://", "ws://")
    ws = websocket.WebSocket()
    ws.connect(f"{ws_url}/ws?clientId={client_id}")
    print(f"WebSocket connected (client_id: {client_id})\n")

    success = 0
    fail    = 0
    t_total = time.time()

    for i in range(1, NUM_IMAGES + 1):
        seed      = random.randint(0, 2**32 - 1)
        t_start   = time.time()

        print(f"[{i:03d}/{NUM_IMAGES}] seed={seed}")

        try:
            api_prompt = build_api_prompt(workflow, seed)
            result     = queue_prompt(api_prompt, client_id)
            prompt_id  = result["prompt_id"]
            print(f"  queued  prompt_id={prompt_id}")

            ok = wait_for_completion(ws, prompt_id)
            if not ok:
                fail += 1
                continue

            # Download images from history
            history = get_history(prompt_id)
            if prompt_id not in history:
                print("  WARNING: prompt_id not in history yet")
                fail += 1
                continue

            outputs = history[prompt_id].get("outputs", {})
            saved   = 0
            for node_id, node_output in outputs.items():
                for img_info in node_output.get("images", []):
                    img_bytes = get_image(
                        img_info["filename"],
                        img_info.get("subfolder", ""),
                        img_info.get("type", "output"),
                    )
                    out_path = os.path.join(SAVE_DIR, img_info["filename"])
                    with open(out_path, "wb") as f:
                        f.write(img_bytes)
                    saved += 1
                    print(f"  saved   {img_info['filename']}  ({len(img_bytes)//1024} KB)")

            dur = time.time() - t_start
            print(f"  done    {saved} image(s) in {dur:.1f}s\n")
            success += 1

        except KeyboardInterrupt:
            print("\nInterrupted by user.")
            break
        except Exception as e:
            print(f"  FAILED: {e}\n")
            fail += 1
            time.sleep(3)  # brief pause before retrying next

    ws.close()

    elapsed = time.time() - t_total
    print("=" * 60)
    print(f"  Done: {success} succeeded, {fail} failed")
    print(f"  Total time: {elapsed/60:.1f} min")
    print(f"  Images saved to: {SAVE_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
