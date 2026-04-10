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

COMFYUI_URL = "https://5r8nlrq0r1pl6j-8188.proxy.runpod.net/"
SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_images", "hari_news")
NUM_IMAGES = 500

RAW_PROMPT_TEXT = (
    "(extreme wide shot, full body visible, sitting wide angle, distant camera:1.5),"
    "01. [QUALITY & MASTERING]: 8K ultra-HD, film-grade quality."

    " 02. [CAMERA & OPTICS]: Shot on a Sony A7R V mirrorless camera paired with a premium 85mm f/1.4 GM lens. The camera angle is a front direct view, establishing a perfectly centered and static composition. It is captured from a medium distance to include both the subject and her immediate desk environment. The aperture is strictly set to f/1.4, generating a highly compressed depth of field that smoothly blurs the background while keeping the subject completely sharp. Perfectly symmetrical frontal portrait, Symmetry, Looking straight into the lens with a 0-degree camera angle."

    "03. [SUBJECT & PHYSIOLOGY]:hari, exuding a confident, sexy tech-influencer aura. an unwavering gaze directly into the lens."

    "04. [WARDROBE & TEXTILE]: Tops: ({crisp white oversized Oxford cotton shirt with rolled-up sleeves|sleek black turtleneck made of high-density merino wool|minimalist grey structured blazer over a matte silk camisole | Black Business suit | Black Leather Jacket with white t-shirt, deep scoop neck | solid | striped | plaid | floral | polka_dot | geometric | sheer | }| ){white | black | gray | beige | tan | blue | navy | red | pastel_pink | pastel_yellow | pastel_green | cream}_ {tshirt, short_sleeve | tank_top, sleeveless | button_shirt, rolled_sleeves | crop_top, fitted | linen_blouse, loose_fit | polo_shirt, collar | camisole, thin_straps}, Outerwear: {({solid | striped | plaid | floral | polka_dot | geometric | sheer | }| ){white | black | gray | beige | tan | blue | navy | red | pastel_pink | pastel_yellow | pastel_green | cream}_ {denim_jacket | light_cardigan | open_shirt} | } "

    "05. [ENVIRONMENT & ARCHITECTURE]: The environment is a meticulously curated high-end tech YouTuber studio setup. A sleek matte black walnut wood desk occupies the immediate foreground, anchoring the composition. In the softly blurred background, subtle RGB accent lighting in cyan and magenta washes over premium acoustic foam panels. A secondary monitor displaying data analytics and a professional broadcast microphone on a boom arm complete the technologically advanced, crisp atmosphere. "

    "06. [ACTION & POSTURE]: The subject is seated perfectly in the center of the frame, maintaining an upright, confident, and highly professional posture. Her shoulders are relaxed, demonstrating a natural ease before recording. Her hands rest delicately on the desk, with her finger joints gently curved. Her gaze is directed exactly at the camera lens, effectively projecting absolute readiness to deliver tech news. "

    "06. [ACTION & POSTURE]: Seated elegantly behind the desk, her posture is relaxed. She leans slightly forward, resting her forearms gently on the desk edge, creating a subtle compression of her top that accentuates her cleavage. Her gaze is locked directly into the lens. Her delicate fingers are subtly intertwined."
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
