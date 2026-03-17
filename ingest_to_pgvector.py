"""
ingest_to_pgvector.py
─────────────────────
하리 페르소나 Q&A 문서를 파싱하여 AWS RDS PostgreSQL(pgvector)에 임베딩 벡터와 함께 적재합니다.

Usage:
  python ingest_to_pgvector.py            # 실제 DB 적재
  python ingest_to_pgvector.py --dry-run  # DB 연결 없이 파싱 결과만 확인
"""

import argparse
import logging
import os
import re
import sys
from typing import Optional

import psycopg2
from dotenv import load_dotenv
from docx import Document
from langchain_openai import OpenAIEmbeddings
from tqdm import tqdm

# ──────────────────────────────────────────────
# 로깅 설정
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 환경 변수 로드
# ──────────────────────────────────────────────
load_dotenv(encoding="utf-8")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "hari_persona")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
# .env에서 한글 경로를 잘못 읽어올 경우를 대비해 None 필터링 후 기본값 사용
persona_env = os.getenv("PERSONA_FILE_PATH")
if persona_env and "" in persona_env:  # 인코딩 깨짐 감지
    persona_env = "하리 페르소나.docx"
PERSONA_FILE_PATH = persona_env or "하리 페르소나.docx"

# LangSmith 추적 (선택)
if os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true":
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    logger.info("LangSmith 추적이 활성화되었습니다. (Project: %s)", os.getenv("LANGCHAIN_PROJECT"))


# ──────────────────────────────────────────────
# 데이터 클래스
# ──────────────────────────────────────────────
class QAChunk:
    """Q&A 의미 단위 청크"""
    def __init__(self, category: str, question: str, answer: str):
        self.category = category.strip()
        self.question = question.strip()
        self.answer = answer.strip()

    def to_embed_text(self) -> str:
        """임베딩할 텍스트: 카테고리 + 질문 + 답변을 하나로 결합"""
        return f"[카테고리: {self.category}]\nQ: {self.question}\nA: {self.answer}"

    def __repr__(self):
        return f"QAChunk(cat='{self.category}', q='{self.question[:30]}...', a='{self.answer[:30]}...')"


# ──────────────────────────────────────────────
# Step 1: 문서 파싱 (Q&A 의미 단위 청킹)
# ──────────────────────────────────────────────
def parse_persona_docx(file_path: str) -> list[QAChunk]:
    """
    Heading 3 스타일 → 카테고리
    Normal 스타일    → '질문? 답변' 형태의 Q&A (물음표 기준으로 분리)
    """
    logger.info("문서 파싱 시작: %s", file_path)
    doc = Document(file_path)

    chunks: list[QAChunk] = []
    current_category = "기타"

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        style_name = para.style.name

        # 카테고리 헤더 감지 (Heading 스타일 또는 번호. 패턴)
        if "Heading" in style_name or re.match(r"^\d+\.", text):
            # "1. 기본 인적사항 (Identity)" → "기본 인적사항 (Identity)" 추출
            match = re.match(r"^\d+\.\s*(.+)", text)
            current_category = match.group(1).strip() if match else text
            logger.debug("카테고리 변경: %s", current_category)
            continue

        # Q&A 파싱: '질문? 답변' 형태에서 마지막 '?'를 기준으로 분리
        # 예: "이름이 뭐야? 강하리" → question="이름이 뭐야", answer="강하리"
        q_split = _split_question_answer(text)
        if q_split:
            question, answer = q_split
            chunks.append(QAChunk(
                category=current_category,
                question=question,
                answer=answer,
            ))
        else:
            # 물음표가 없는 문단은 이전 청크의 보조 답변으로 처리하거나 건너뜀
            if chunks:
                chunks[-1].answer += " " + text
            logger.debug("물음표 없는 문단 처리(이전 chunk에 추가): %s", text[:60])

    logger.info("총 %d개의 Q&A 청크 파싱 완료.", len(chunks))
    return chunks


def _split_question_answer(text: str) -> Optional[tuple[str, str]]:
    """
    문자열에서 첫 번째 물음표(?) 위치를 기준으로 (질문, 답변) 분리.
    물음표가 없으면 None 반환.
    """
    idx = text.find("?")
    if idx == -1:
        return None
    question = text[:idx].strip()
    answer = text[idx + 1:].strip()
    if not answer:
        return None
    return question, answer


# ──────────────────────────────────────────────
# Step 2: DB 초기화 (테이블 + 인덱스 생성)
# ──────────────────────────────────────────────
def init_database(conn) -> None:
    """pgvector 익스텐션 활성화, hari_knowledge 테이블 및 HNSW 인덱스 생성"""
    logger.info("데이터베이스 스키마 초기화 중...")
    with conn.cursor() as cur:
        # pgvector 확장 활성화
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        # 테이블 생성
        # text-embedding-3-small 차원 = 1536
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hari_knowledge (
                id              BIGSERIAL PRIMARY KEY,
                category        TEXT         NOT NULL,
                question        TEXT         NOT NULL,
                answer          TEXT         NOT NULL,
                content_vector  VECTOR(1536)
            );
        """)

        # HNSW 인덱스 생성 (코사인 유사도 기반 검색 최적화)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_hari_knowledge_hnsw
            ON hari_knowledge
            USING hnsw (content_vector vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """)

    conn.commit()
    logger.info("DB 스키마 초기화 완료.")


# ──────────────────────────────────────────────
# Step 3: 임베딩 생성
# ──────────────────────────────────────────────
def embed_chunks(chunks: list[QAChunk]) -> list[list[float]]:
    """OpenAI text-embedding-3-small 모델로 각 청크 벡터화"""
    logger.info("임베딩 생성 시작 (모델: text-embedding-3-small, 청크 수: %d)", len(chunks))
    embeddings_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=OPENAI_API_KEY,
    )
    texts = [chunk.to_embed_text() for chunk in chunks]

    try:
        vectors = embeddings_model.embed_documents(texts)
        logger.info("임베딩 완료. 벡터 차원: %d", len(vectors[0]) if vectors else 0)
        return vectors
    except Exception as e:
        logger.error("임베딩 생성 중 오류 발생: %s", e)
        raise


# ──────────────────────────────────────────────
# Step 4: DB 적재
# ──────────────────────────────────────────────
def insert_chunks(conn, chunks: list[QAChunk], vectors: list[list[float]]) -> None:
    """파싱된 Q&A와 임베딩 벡터를 hari_knowledge 테이블에 배치 Insert"""
    logger.info("DB 적재 시작 (총 %d건)...", len(chunks))

    INSERT_SQL = """
        INSERT INTO hari_knowledge (category, question, answer, content_vector)
        VALUES (%s, %s, %s, %s::vector)
        ON CONFLICT DO NOTHING;
    """

    with conn.cursor() as cur:
        for chunk, vector in tqdm(zip(chunks, vectors), total=len(chunks), desc="Inserting"):
            try:
                # psycopg2에 벡터를 넘길 때 pgvector 형식으로 변환
                vector_str = "[" + ",".join(str(v) for v in vector) + "]"
                cur.execute(INSERT_SQL, (
                    chunk.category,
                    chunk.question,
                    chunk.answer,
                    vector_str,
                ))
            except Exception as e:
                logger.warning("레코드 삽입 실패 (category=%s, q=%s): %s", chunk.category, chunk.question[:30], e)
                conn.rollback()
                continue

    conn.commit()
    logger.info("DB 적재 완료.")


# ──────────────────────────────────────────────
# Step 5: DB 연결
# ──────────────────────────────────────────────
def get_db_connection():
    """환경 변수에서 접속 정보를 읽어 PostgreSQL 연결 반환"""
    missing = [k for k, v in {
        "DB_HOST": DB_HOST,
        "DB_USER": DB_USER,
        "DB_PASSWORD": DB_PASSWORD,
    }.items() if not v]

    if missing:
        raise EnvironmentError(f".env에 다음 변수가 누락되어 있습니다: {', '.join(missing)}")

    logger.info("DB 연결 시도: %s:%s/%s (user=%s)", DB_HOST, DB_PORT, DB_NAME, DB_USER)
    return psycopg2.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=10,
    )


# ──────────────────────────────────────────────
# 메인 엔트리포인트
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="하리 페르소나 Q&A → pgvector 수집 파이프라인")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="DB에 적재하지 않고 파싱 및 임베딩 결과만 확인합니다.",
    )
    args = parser.parse_args()

    # ── 1. 문서 파싱
    try:
        chunks = parse_persona_docx(PERSONA_FILE_PATH)
    except FileNotFoundError:
        logger.error("페르소나 파일을 찾을 수 없습니다: %s", PERSONA_FILE_PATH)
        sys.exit(1)

    if not chunks:
        logger.error("파싱된 Q&A 청크가 없습니다. 문서 형식을 확인하세요.")
        sys.exit(1)

    # 파싱 결과 미리보기
    logger.info("── 파싱 결과 미리보기 (최초 5건) ──")
    for i, chunk in enumerate(chunks[:5]):
        logger.info("[%d] %s", i + 1, chunk)

    # ── dry-run 모드
    if args.dry_run:
        logger.info("\n[DRY-RUN] 파싱 완료. 총 %d개 청크. DB 적재를 건너뜁니다.", len(chunks))
        logger.info("[DRY-RUN] 임베딩 생성 테스트 (첫 번째 청크만)...")
        try:
            test_vectors = embed_chunks(chunks[:1])
            logger.info("[DRY-RUN] 임베딩 성공. 벡터 차원: %d", len(test_vectors[0]))
        except Exception as e:
            logger.error("[DRY-RUN] 임베딩 실패: %s", e)
        return

    # ── 2. 임베딩 생성
    try:
        vectors = embed_chunks(chunks)
    except Exception as e:
        logger.error("임베딩 생성 실패로 파이프라인을 중단합니다: %s", e)
        sys.exit(1)

    # ── 3. DB 연결 및 초기화
    try:
        conn = get_db_connection()
    except Exception as e:
        logger.error("DB 연결 실패: %s", e)
        sys.exit(1)

    try:
        init_database(conn)

        # ── 4. DB 적재
        insert_chunks(conn, chunks, vectors)

        # ── 5. 결과 검증
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM hari_knowledge;")
            count = cur.fetchone()[0]
        logger.info("최종 hari_knowledge 테이블 레코드 수: %d", count)

    except Exception as e:
        logger.error("파이프라인 실행 중 예기치 않은 오류: %s", e)
        conn.rollback()
        raise
    finally:
        conn.close()
        logger.info("DB 연결 종료.")

    logger.info("파이프라인 완료!")


if __name__ == "__main__":
    main()
