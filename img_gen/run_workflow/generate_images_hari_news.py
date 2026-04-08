"""
Generate 500 images using the 하리_뉴스용 workflow via ComfyUI API.
"""

import json
import os
import random
import re
import time

import requests
import websocket  # pip install websocket-client

# ── Config ────────────────────────────────────────────────────────────────────

COMFYUI_URL = "https://46xac66ib5gbki-8188.proxy.runpod.net"
SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_images", "hari_news")
NUM_IMAGES = 500

RAW_PROMPT_TEXT = (
    "hari, (extreme wide shot, full body visible, sitting wide angle, distant camera:1.5),\n"
    "01. [QUALITY & MASTERING]: 8K ultra-HD, film-grade quality, grainless precision, high-contrast cinematic color grading with cool-toned tech aesthetics. The image must exhibit unparalleled sharpness and hyper-realistic rendering, ensuring zero chromatic aberration. The color palette should emphasize sleek modern tones like matte black, silver, and soft neon accents. Every pixel must reflect a pristine, commercial-grade YouTube production standard. 02. [CAMERA & OPTICS]: Shot on a Sony A7S III with a 24mm f/1.4 G Master lens to achieve a sitting wide-angle perspective and a distant camera:1.5 effect. The aperture is set to f/2.8 to maintain a crisp focus on the subject while creating a smooth, subtle bokeh in the background tech setup. The sensor captures an expansive dynamic range, preserving intricate details in both the brightly lit face and the shadowed desk areas. The front-view direct angle ensures a perfectly symmetrical composition. 03. [SUBJECT & PHYSIOLOGY]: [SUBJECT]: 20yo Korean female, 168cm height, perfect 8-head body proportion, extremely small head size, narrow feminine shoulders, voluptuous curves, cinched waist, pristine porcelain skin, none. Her facial features are highly symmetrical with a neutral ivory complexion, absolutely zero redness or blushing. Her expression is completely serious with no smile and lips firmly closed, conveying a professional and focused demeanor. The hyper-detailed rendering captures the microscopic peach fuzz on her jawline and the matte finish of her foundation perfectly. 04. [WARDROBE & TEXTILE]: She is wearing a {crisp white oversized Oxford cotton shirt with rolled-up sleeves|sleek black turtleneck made of high-density merino wool|minimalist grey structured blazer over a matte silk camisole | Black Business suit | Micro size Bikini | Leather Jacket with white t-shirt, deep scoop neck} specifically framing her upper body. The fabric drapes naturally over her narrow shoulders, displaying realistic tension folds around the chest and arms. The micro-texture of the chosen garment interacts flawlessly with the studio lighting, highlighting the premium quality of the material. A subtle metallic glint from a minimalist silver smartwatch adds a touch of tech-savvy professionalism to her wrist. 05. [ENVIRONMENT & ARCHITECTURE]: The setting is a premium tech vlogger's studio, viewed from behind a sleek matte-black oak desk. High-end peripherals, such as a mechanical keyboard with brushed aluminum chassis and a precision mouse, are neatly arranged on the desk surface directly in front of her. The background features acoustic dampening panels and a subtly glowing monitor setup, establishing a modern, professional atmosphere. The ambient air feels cool and dust-free, perfectly suited for high-end electronics and concentrated work. 06. [ACTION & POSTURE]: She is seated in an ergonomic mesh office chair, maintaining a perfectly straight alignment of her legs, pelvis, waist, and head facing directly towards the camera. Her posture is relaxed yet highly disciplined, with her upper body resting comfortably but symmetrically. Her hands are gently placed on the desk near the keyboard, fingers slightly curved in a natural resting state. Her gaze is locked dead-center into the lens with an unwavering, professional intensity."
)

# ── Wildcard resolver ─────────────────────────────────────────────────────────

def resolve_wildcards(text: str) -> str:
    """Replace {a|b|c} patterns with a random choice."""
    def pick(m: re.Match) -> str:
        return random.choice(m.group(1).split("|")).strip()
    while "{" in text:
        text = re.sub(r"\{([^{}]+)\}", pick, text)
    return text

# ── API prompt builder ────────────────────────────────────────────────────────

def build_api_prompt(seed: int) -> dict:
    return {
        "63": {  # VAELoader
            "class_type": "VAELoader",
            "inputs": {"vae_name": "ae.safetensors"},
        },
        "66": {  # UNETLoader
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "z_image_turbo_bf16.safetensors",
                "weight_dtype": "default",
            },
        },
        "62": {  # CLIPLoader
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": "qwen_3_4b.safetensors",
                "type": "lumina2",
                "device": "default",
            },
        },
        "71": {  # LoraLoader
            "class_type": "LoraLoader",
            "inputs": {
                "model": ["66", 0],
                "clip": ["62", 0],
                "lora_name": "hari_v1.safetensors",
                "strength_model": 1,
                "strength_clip": 1,
            },
        },
        "67": {  # CLIPTextEncode (positive)
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["71", 1],
                "text": resolve_wildcards(RAW_PROMPT_TEXT),
            },
        },
        "64": {  # ConditioningZeroOut (negative)
            "class_type": "ConditioningZeroOut",
            "inputs": {"conditioning": ["67", 0]},
        },
        "68": {  # EmptySD3LatentImage
            "class_type": "EmptySD3LatentImage",
            "inputs": {"width": 1024, "height": 1024, "batch_size": 1},
        },
        "69": {  # ModelSamplingAuraFlow
            "class_type": "ModelSamplingAuraFlow",
            "inputs": {"shift": 3, "model": ["71", 0]},
        },
        "70": {  # KSampler
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": 8,
                "cfg": 1,
                "sampler_name": "res_multistep",
                "scheduler": "simple",
                "denoise": 1,
                "model": ["69", 0],
                "positive": ["67", 0],
                "negative": ["64", 0],
                "latent_image": ["68", 0],
            },
        },
        "65": {  # VAEDecode
            "class_type": "VAEDecode",
            "inputs": {"samples": ["70", 0], "vae": ["63", 0]},
        },
        "9": {  # SaveImage
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": f"hari_news_{seed}",
                "images": ["65", 0],
            },
        },
    }

# ── ComfyUI helpers ───────────────────────────────────────────────────────────

def queue_prompt(api_prompt: dict, client_id: str) -> dict:
    payload = {"prompt": api_prompt, "client_id": client_id}
    response = requests.post(f"{COMFYUI_URL}/prompt", json=payload)
    response.raise_for_status()
    return response.json()


def get_image(filename: str, subfolder: str, folder_type: str) -> bytes:
    params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    response = requests.get(f"{COMFYUI_URL}/view", params=params)
    response.raise_for_status()
    return response.content


def get_history(prompt_id: str) -> dict:
    response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}")
    response.raise_for_status()
    return response.json()


def wait_for_completion(ws: websocket.WebSocket, prompt_id: str) -> bool:
    while True:
        raw = ws.recv()
        if isinstance(raw, bytes):
            continue
        msg = json.loads(raw)
        if msg.get("type") == "executing":
            data = msg.get("data", {})
            if data.get("prompt_id") == prompt_id and data.get("node") is None:
                return True  # finished
        elif msg.get("type") == "execution_error":
            data = msg.get("data", {})
            if data.get("prompt_id") == prompt_id:
                print(f"  ERROR: {data}")
                return False

# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    os.makedirs(SAVE_DIR, exist_ok=True)

    print("=" * 60)
    print(f"  Workflow : 하리_뉴스용")
    print(f"  Server   : {COMFYUI_URL}")
    print(f"  Total    : {NUM_IMAGES} images")
    print(f"  Save dir : {SAVE_DIR}")
    print("=" * 60)

    # Verify server is reachable
    try:
        resp = requests.get(f"{COMFYUI_URL}/system_stats", timeout=10)
        resp.raise_for_status()
        print("Server reachable.\n")
    except Exception as e:
        print(f"Cannot reach ComfyUI server: {e}")
        return

    client_id = f"batch_{random.randint(0, 999999):06d}"

    ws_url = COMFYUI_URL.rstrip("/").replace("https://", "wss://").replace("http://", "ws://")
    ws = websocket.WebSocket()
    ws.connect(f"{ws_url}/ws?clientId={client_id}")
    print(f"WebSocket connected (client_id: {client_id})\n")

    success = 0
    fail = 0

    try:
        for i in range(1, NUM_IMAGES + 1):
            seed = random.randint(0, 2**53 - 1)
            print(f"[{i:>3}/{NUM_IMAGES}] seed={seed}")

            api_prompt = build_api_prompt(seed)

            try:
                result = queue_prompt(api_prompt, client_id)
                prompt_id = result["prompt_id"]
                print(f"  queued  prompt_id={prompt_id}")
            except Exception as e:
                print(f"  FAILED to queue: {e}")
                fail += 1
                continue

            ok = wait_for_completion(ws, prompt_id)
            if not ok:
                print("  FAILED during generation")
                fail += 1
                continue

            # Download and save
            try:
                history = get_history(prompt_id)
                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    saved = False
                    for node_id, node_output in outputs.items():
                        images = node_output.get("images", [])
                        for img_info in images:
                            img_bytes = get_image(
                                img_info["filename"],
                                img_info.get("subfolder", ""),
                                img_info.get("type", "output"),
                            )
                            save_path = os.path.join(SAVE_DIR, f"{seed}.png")
                            with open(save_path, "wb") as f:
                                f.write(img_bytes)
                            print(f"  saved   {save_path}  ({len(img_bytes)//1024} KB)")
                            saved = True
                    if not saved:
                        print("  WARNING: SaveImage output not found in history")
                        fail += 1
                        continue
                else:
                    print("  WARNING: prompt_id not in history")
                    fail += 1
                    continue
            except Exception as e:
                print(f"  FAILED to download: {e}")
                fail += 1
                continue

            success += 1
            time.sleep(0.2)

    finally:
        ws.close()

    print("\n" + "=" * 60)
    print(f"  Done  success={success}  fail={fail}")
    print(f"  Saved to: {SAVE_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
