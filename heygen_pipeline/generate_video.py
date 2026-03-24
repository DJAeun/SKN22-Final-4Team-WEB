"""
HeyGen 아바타 영상 자동 생성 파이프라인 (WAV 오디오 입력 버전)

[흐름]
  1. WAV 파일 → MP3 변환 (ffmpeg)
  2. MP3 → HeyGen Upload Asset API로 업로드 → audio_asset_id 획득
  3. HeyGen API → talking_photo + audio 기반 영상 생성
  4. 렌더링 대기 → 영상 다운로드

[필요 사전조건]
  - ffmpeg 가 PATH에 있어야 함
    Windows: https://ffmpeg.org/download.html 에서 설치 후 PATH 등록
"""

import requests
import time
import os
import json
import sys
import subprocess
import glob
from datetime import datetime


# ============================================================
# 설정
# ============================================================
API_KEY = "sk_V2_hgu_kXf2VFgX4hI_M4YZKY7V8EZ9SeIng3FJP58yVOkpC04K"
BASE_URL = "https://api.heygen.com"
UPLOAD_URL = "https://upload.heygen.com/v1/asset"
HEADERS = {
    "X-Api-Key": API_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json",
}

RAPI_TALKING_PHOTO_ID = "ee354bb52158453d80822a4b76b77768"

INPUT_AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input_audio")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_videos")
os.makedirs(INPUT_AUDIO_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# 1. WAV → MP3 변환
# ============================================================
def convert_wav_to_mp3(wav_path: str) -> str:
    """ffmpeg으로 WAV를 MP3로 변환. 변환된 MP3 경로 반환."""
    mp3_path = os.path.splitext(wav_path)[0] + ".mp3"
    cmd = [
        "ffmpeg", "-y",
        "-i", wav_path,
        "-codec:a", "libmp3lame",
        "-qscale:a", "2",  # 고품질 VBR
        mp3_path,
    ]
    print(f"\n🔄 WAV → MP3 변환 중... → {os.path.basename(mp3_path)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg WAV→MP3 변환 실패: {result.stderr.strip()}")
    print(f"   ✅ 변환 완료! ({os.path.getsize(mp3_path):,} bytes)")
    return mp3_path


# ============================================================
# 2. HeyGen Upload Asset API로 오디오 업로드
# ============================================================
def upload_audio_to_heygen(mp3_path: str) -> str:
    """MP3 파일을 HeyGen에 업로드하고 audio_asset_id 반환."""
    print(f"\n☁️  HeyGen에 오디오 업로드 중... ({os.path.basename(mp3_path)})")

    with open(mp3_path, "rb") as f:
        data = f.read()

    headers = {
        "X-Api-Key": API_KEY,
        "Content-Type": "audio/mpeg",
    }
    resp = requests.post(UPLOAD_URL, headers=headers, data=data)

    resp.raise_for_status()
    result = resp.json()

    asset_id = result.get("data", {}).get("asset_id") or result.get("data", {}).get("id")
    if not asset_id:
        raise RuntimeError(
            f"오디오 업로드 실패 — asset_id를 받지 못했습니다:\n"
            f"{json.dumps(result, indent=2, ensure_ascii=False)}"
        )

    print(f"   ✅ 업로드 완료! asset_id: {asset_id}")
    return asset_id


# ============================================================
# 3. HeyGen 영상 생성 요청 (오디오 기반)
# ============================================================
def generate_video(audio_asset_id: str) -> str | None:
    """talking_photo + 업로드된 오디오로 영상 생성 (숏폼 9:16)"""
    url = f"{BASE_URL}/v2/video/generate"

    payload = {
        "video_inputs": [
            {
                "character": {
                    "type": "talking_photo",
                    "talking_photo_id": RAPI_TALKING_PHOTO_ID,
                    "use_avatar_iv_model": True,  # Avatar IV 엔진 활성화 (왜곡 감소, 품질 향상)
                },
                "voice": {
                    "type": "audio",
                    "audio_asset_id": audio_asset_id,
                },
            }
        ],
        "dimension": {"width": 1080, "height": 1920},
        "caption": False,
    }

    print("\n🎬 HeyGen 영상 생성 요청 중 (Audio 기반)...")
    resp = requests.post(url, headers=HEADERS, json=payload)
    resp.raise_for_status()
    result = resp.json()

    video_id = result.get("data", {}).get("video_id")
    if not video_id:
        print(f"❌ 생성 요청 실패:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
        return None

    print(f"   ✅ video_id: {video_id}")
    return video_id


# ============================================================
# 4. 렌더링 대기
# ============================================================
def wait_for_video(video_id: str, poll_interval: int = 10, max_wait: int = 900) -> str | None:
    url = f"{BASE_URL}/v1/video_status.get"
    params = {"video_id": video_id}

    print(f"\n⏳ 렌더링 대기 중... (최대 {max_wait // 60}분)")
    start = time.time()

    while True:
        elapsed = time.time() - start
        if elapsed > max_wait:
            print("❌ 타임아웃!")
            return None

        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        status = data.get("status", "unknown")
        video_url = data.get("video_url")

        m, s = divmod(int(elapsed), 60)
        print(f"   [{m:02d}:{s:02d}] {status}")

        if status == "completed" and video_url:
            print("✅ 렌더링 완료!")
            return video_url
        elif status == "failed":
            print(f"❌ 실패: {data.get('error', '?')}")
            return None

        time.sleep(poll_interval)


# ============================================================
# 5. 영상 다운로드
# ============================================================
def download_video(video_url: str, filename: str) -> str:
    filepath = os.path.join(OUTPUT_DIR, filename)
    print(f"\n💾 다운로드 중... → {filepath}")

    resp = requests.get(video_url, stream=True)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))
    dl = 0
    with open(filepath, "wb") as f:
        for chunk in resp.iter_content(8192):
            f.write(chunk)
            dl += len(chunk)
            if total:
                print(f"\r   {dl / total * 100:.1f}%", end="")
    print(f"\n   ✅ 저장 완료! ({os.path.getsize(filepath):,} bytes)")
    return filepath


# ============================================================
# 파이프라인 실행
# ============================================================
def run_pipeline(wav_path: str | None = None):
    """
    WAV 오디오 기반 HeyGen 영상 생성 파이프라인.

    Args:
        wav_path: WAV 파일 경로. None이면 input_audio 폴더에서 최신 파일 사용.
    """
    # WAV 파일 결정
    if wav_path is None:
        wav_files = glob.glob(os.path.join(INPUT_AUDIO_DIR, "*.wav"))
        if not wav_files:
            print(f"❌ '{INPUT_AUDIO_DIR}' 폴더에 WAV 파일이 없습니다.")
            print("   사용법: python generate_video.py [wav파일경로]")
            return None
        wav_path = sorted(wav_files)[-1]

    if not os.path.exists(wav_path):
        print(f"❌ WAV 파일을 찾을 수 없습니다: {wav_path}")
        return None

    print("=" * 60)
    print("🚀 HeyGen 숏폼(9:16) WAV 오디오 기반 영상 생성")
    print("=" * 60)
    print(f"📂 입력 오디오: {wav_path}")

    # ── Step 1: WAV → MP3 변환
    mp3_path = convert_wav_to_mp3(wav_path)

    # ── Step 2: HeyGen에 오디오 업로드
    audio_asset_id = upload_audio_to_heygen(mp3_path)

    # ── Step 3: HeyGen 영상 생성
    video_id = generate_video(audio_asset_id)
    if not video_id:
        return None

    # ── Step 4: 렌더링 대기
    video_url = wait_for_video(video_id)
    if not video_url:
        return None

    # ── Step 5: 영상 다운로드
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_path = download_video(video_url, f"final_{ts}.mp4")

    print("\n" + "=" * 60)
    print("🎉 전체 완료!")
    print(f"   📂 최종 영상 : {final_path}")
    print("=" * 60)
    return final_path


# ============================================================
# 실행
# ============================================================
if __name__ == "__main__":
    # 커맨드라인 인자로 WAV 파일 경로 전달 가능
    wav = sys.argv[1] if len(sys.argv) > 1 else None
    run_pipeline(wav_path=wav)
