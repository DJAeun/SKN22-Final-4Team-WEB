"""
디버그: 에러 응답 상세 출력
"""
import json
import requests
import random
import sys

COMFYUI_URL = "https://c4z197av3ovxo5-8188.proxy.runpod.net"

# 가장 단순한 1단계 테스트 - 단 하나의 클래스만 테스트
api_prompt = {
    "1": {
        "class_type": "LoadImage",
        "inputs": {
            "image": "MSE4KG2501BK_M.jpg"
        }
    },
    "2": {
        "class_type": "UNETLoader",
        "inputs": {
            "unet_name": "flux-2-klein-4b-fp8.safetensors",
            "weight_dtype": "default"
        }
    },
    "3": {
        "class_type": "CLIPLoader",
        "inputs": {
            "clip_name": "qwen_3_4b.safetensors",
            "type": "flux2",
            "device": "default"
        }
    },
    "4": {
        "class_type": "VAELoader",
        "inputs": {
            "vae_name": "flux2-vae.safetensors"
        }
    },
    "5": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "test clothing change",
            "clip": ["3", 0]
        }
    },
    "6": {
        "class_type": "ConditioningZeroOut",
        "inputs": {
            "conditioning": ["5", 0]
        }
    },
    "7": {
        "class_type": "ImageScaleToTotalPixels",
        "inputs": {
            "upscale_method": "nearest-exact",
            "megapixels": 1,
            "image": ["1", 0]
        }
    },
    "8": {
        "class_type": "GetImageSize",
        "inputs": {
            "image": ["7", 0]
        }
    },
    "9": {
        "class_type": "VAEEncode",
        "inputs": {
            "pixels": ["7", 0],
            "vae": ["4", 0]
        }
    },
    "10": {
        "class_type": "ReferenceLatent",
        "inputs": {
            "conditioning": ["5", 0],
            "latent": ["9", 0]
        }
    },
    "11": {
        "class_type": "ReferenceLatent",
        "inputs": {
            "conditioning": ["6", 0],
            "latent": ["9", 0]
        }
    },
    "12": {
        "class_type": "Flux2Scheduler",
        "inputs": {
            "steps": 4,
            "width": ["8", 0],
            "height": ["8", 1]
        }
    },
    "13": {
        "class_type": "EmptyFlux2LatentImage",
        "inputs": {
            "width": ["8", 0],
            "height": ["8", 1],
            "batch_size": 1
        }
    },
    "14": {
        "class_type": "CFGGuider",
        "inputs": {
            "cfg": 1,
            "model": ["2", 0],
            "positive": ["10", 0],
            "negative": ["11", 0]
        }
    },
    "15": {
        "class_type": "RandomNoise",
        "inputs": {
            "noise_seed": 12345
        }
    },
    "16": {
        "class_type": "KSamplerSelect",
        "inputs": {
            "sampler_name": "euler"
        }
    },
    "17": {
        "class_type": "SamplerCustomAdvanced",
        "inputs": {
            "noise": ["15", 0],
            "guider": ["14", 0],
            "sampler": ["16", 0],
            "sigmas": ["12", 0],
            "latent_image": ["13", 0]
        }
    },
    "18": {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": ["17", 0],
            "vae": ["4", 0]
        }
    },
    "19": {
        "class_type": "SaveImage",
        "inputs": {
            "filename_prefix": "debug_test",
            "images": ["18", 0]
        }
    }
}

client_id = f"debug_{random.randint(0, 999999):06d}"
payload = {"prompt": api_prompt, "client_id": client_id}

sys.stdout.write("Sending to ComfyUI...\n")
sys.stdout.flush()

try:
    response = requests.post(f"{COMFYUI_URL}/prompt", json=payload, timeout=30)
    sys.stdout.write(f"HTTP Status: {response.status_code}\n")
    sys.stdout.write(f"Response:\n{response.text}\n")
    sys.stdout.flush()
except Exception as e:
    sys.stdout.write(f"Request Exception: {e}\n")
    sys.stdout.flush()

# object_info에서 ReferenceLatent 입력 파라미터 확인
sys.stdout.write("\n=== ReferenceLatent node info ===\n")
sys.stdout.flush()
try:
    resp = requests.get(f"{COMFYUI_URL}/object_info/ReferenceLatent", timeout=15)
    sys.stdout.write(f"{json.dumps(resp.json(), indent=2, ensure_ascii=False)[:3000]}\n")
    sys.stdout.flush()
except Exception as e:
    sys.stdout.write(f"Error: {e}\n")
    sys.stdout.flush()

# Flux2Scheduler info
sys.stdout.write("\n=== Flux2Scheduler node info ===\n")
sys.stdout.flush()
try:
    resp = requests.get(f"{COMFYUI_URL}/object_info/Flux2Scheduler", timeout=15)
    sys.stdout.write(f"{json.dumps(resp.json(), indent=2, ensure_ascii=False)[:2000]}\n")
    sys.stdout.flush()
except Exception as e:
    sys.stdout.write(f"Error: {e}\n")
    sys.stdout.flush()
    
# EmptyFlux2LatentImage info
sys.stdout.write("\n=== EmptyFlux2LatentImage node info ===\n")
sys.stdout.flush()
try:
    resp = requests.get(f"{COMFYUI_URL}/object_info/EmptyFlux2LatentImage", timeout=15)
    sys.stdout.write(f"{json.dumps(resp.json(), indent=2, ensure_ascii=False)[:2000]}\n")
    sys.stdout.flush()
except Exception as e:
    sys.stdout.write(f"Error: {e}\n")
    sys.stdout.flush()

# GetImageSize info
sys.stdout.write("\n=== GetImageSize node info ===\n")
sys.stdout.flush()
try:
    resp = requests.get(f"{COMFYUI_URL}/object_info/GetImageSize", timeout=15)
    sys.stdout.write(f"{json.dumps(resp.json(), indent=2, ensure_ascii=False)[:2000]}\n")
    sys.stdout.flush()
except Exception as e:
    sys.stdout.write(f"Error: {e}\n")
    sys.stdout.flush()
