# dino_test.py
import os
import torch
import numpy as np
from PIL import Image
from pathlib import Path
from transformers import Dinov2Model, AutoImageProcessor
from sklearn.metrics.pairwise import cosine_similarity
from facenet_pytorch import MTCNN
import warnings
warnings.filterwarnings("ignore")

# ─── 경로 설정 ───────────────────────────────────────────────
DATASET_DIR = "/workspace/runpod-slim/ComfyUI/models/loras/dataset"   # 원본 데이터셋
OUTPUT_DIR  = "/workspace/runpod-slim/ComfyUI/models/loras/output"    # LoRA 생성 이미지

FACE_IMG_SIZE = 518
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[INFO] Device: {DEVICE}")
# ─── 모델 로드 ───────────────────────────────────────────────
print("[INFO] MTCNN 얼굴 감지기 로드 중...")
mtcnn = MTCNN(
    keep_all=False,
    device=DEVICE,
    min_face_size=40,
    thresholds=[0.6, 0.7, 0.7],
    post_process=False,
)
MODEL_NAME = "facebook/dinov2-base"
print(f"[INFO] DINOv2 모델 로드 중: {MODEL_NAME}")
processor = AutoImageProcessor.from_pretrained(MODEL_NAME)

model     = Dinov2Model.from_pretrained(MODEL_NAME).to(DEVICE)
model.eval()
# ─── 얼굴 감지 & 크롭 ────────────────────────────────────────
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
def detect_and_crop_face(img: Image.Image, path: str) -> Image.Image | None:
    """MTCNN으로 bbox 추출 → 크롭 → 리사이즈"""
    boxes, _ = mtcnn.detect(img)
    if boxes is None:
        print(f"  [WARN] 얼굴 미감지: {Path(path).name}")
        return None
    # 가장 큰 얼굴 박스 선택
    box = sorted(boxes, key=lambda b: (b[2]-b[0])*(b[3]-b[1]), reverse=True)[0]
    x1, y1, x2, y2 = [int(v) for v in box]
    # ±10% 패딩
    w, h = x2 - x1, y2 - y1
    pad_x, pad_y = int(w * 0.1), int(h * 0.1)
    W, H = img.size
    x1 = max(0, x1 - pad_x)
    y1 = max(0, y1 - pad_y)
    x2 = min(W, x2 + pad_x)
    y2 = min(H, y2 + pad_y)
    face_crop = img.crop((x1, y1, x2, y2)).resize(
    (518, 518), Image.LANCZOS   # 224 → 518
)
    return face_crop
# ─── 이미지 로드 & 얼굴 크롭 ─────────────────────────────────
def load_face_crops(directory: str) -> list[tuple[str, Image.Image]]:
    paths = sorted([
        p for p in Path(directory).rglob("*")
        if p.suffix.lower() in EXTENSIONS
    ])
    results = []
    for p in paths:
        try:
            img  = Image.open(p).convert("RGB")
            face = detect_and_crop_face(img, str(p))
            if face:
                results.append((str(p), face))
        except Exception as e:
            print(f"  [ERROR] {p.name}: {e}")
    print(f"  → 얼굴 감지 성공: {len(results)}/{len(paths)}장  ({directory})")
    return results
# ─── DINOv2 임베딩 추출 ──────────────────────────────────────
@torch.no_grad()
def extract_embeddings(face_imgs: list[tuple[str, Image.Image]]) -> np.ndarray:
    embeddings = []
    for _, face in face_imgs:
        inputs  = processor(images=face, return_tensors="pt").to(DEVICE)
        outputs = model(**inputs)
        cls_emb = outputs.last_hidden_state[:, 0, :].squeeze().cpu().numpy()
        embeddings.append(cls_emb)
    return np.array(embeddings)
# ─── 메인 평가 ────────────────────────────────────────────────
print("\n[1] 이미지 로드 & 얼굴 감지 중...")
print("  [원본 데이터셋]")
dataset_faces = load_face_crops(DATASET_DIR)
print("  [생성 이미지]")
output_faces  = load_face_crops(OUTPUT_DIR)
if not dataset_faces or not output_faces:
    raise ValueError("얼굴이 감지된 이미지가 없습니다. 경로 또는 이미지 품질을 확인하세요.")
print("\n[2] DINOv2 임베딩 추출 중...")
print("  원본 데이터셋 임베딩...")
dataset_embs = extract_embeddings(dataset_faces)
print("  생성 이미지 임베딩...")
output_embs  = extract_embeddings(output_faces)
# ─── DINO Score 계산 ─────────────────────────────────────────
print("\n[3] DINO Score 계산 중...")
sim_matrix = cosine_similarity(dataset_embs, output_embs)
dino_score_mean = sim_matrix.mean()
dino_score_max  = sim_matrix.max(axis=0).mean()   # 각 생성 이미지의 best match 평균
# ─── 결과 출력 ───────────────────────────────────────────────
print("\n" + "="*55)
print("            DINOv2 얼굴 유사도 평가 결과")
print("="*55)
print(f"  원본 이미지 (얼굴 감지) : {len(dataset_faces)}장")
print(f"  생성 이미지 (얼굴 감지) : {len(output_faces)}장")
print(f"  DINO Score (전체 평균)  : {dino_score_mean:.4f}")
print(f"  DINO Score (Best Match) : {dino_score_max:.4f}")
print("="*55)
print()
print("  점수 해석 기준:")
print("  0.90 이상  → 매우 우수한 신원 보존")
print("  0.80~0.90  → 양호한 신원 보존")
print("  0.70~0.80  → 보통 (추가 학습 권장)")
print("  0.70 미만  → 낮음 (학습 파라미터 재조정 필요)")
print()
# ─── 개별 생성 이미지 상세 결과 ──────────────────────────────
print("[4] 개별 생성 이미지 점수 (Best Match 기준):")
print("-"*55)
for i, (path, _) in enumerate(output_faces):
    best_sim  = sim_matrix[:, i].max()
    best_idx  = sim_matrix[:, i].argmax()
    best_src  = Path(dataset_faces[best_idx][0]).name
    fname     = Path(path).name
    bar       = "█" * int(best_sim * 20)
    print(f"  {fname:<30} {best_sim:.4f} {bar}")
    print(f"  {'':30} └─ best match: {best_src}")
print("\n[완료]")