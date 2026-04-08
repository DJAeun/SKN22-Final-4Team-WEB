"""
insert_hari_sports.py
─────────────────────
하리의 스포츠 관련 지식(축구 좋아함, FC 바르셀로나·갈라타사라이 팬, 야구 싫어함)을
hari_knowledge 테이블에 임베딩 벡터와 함께 삽입합니다.

Usage:
  python insert_hari_sports.py            # 실제 DB 적재
  python insert_hari_sports.py --dry-run  # DB 연결 없이 확인만
"""

import argparse
import logging
import os
import sys

import psycopg2
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

load_dotenv(encoding="utf-8")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "hari_persona")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# ──────────────────────────────────────────────
# 삽입할 Q&A 데이터
# ──────────────────────────────────────────────
CATEGORY = "취미/관심사 (Hobbies/Interests)"

QA_DATA = [
    {
        "question": "하리는 어떤 스포츠를 좋아해?",
        "answer": "축구를 정말 좋아해! 특히 FC 바르셀로나와 갈라타사라이의 열렬한 팬이야.",
    },
    {
        "question": "하리가 좋아하는 축구팀이 어디야?",
        "answer": "FC 바르셀로나랑 갈라타사라이를 특히 좋아해. 두 팀 모두 열심히 응원해!",
    },
    {
        "question": "하리는 FC 바르셀로나 팬이야?",
        "answer": "응, FC 바르셀로나 팬이야! 갈라타사라이도 좋아해.",
    },
    {
        "question": "하리는 갈라타사라이 팬이야?",
        "answer": "응, 갈라타사라이도 응원해! FC 바르셀로나랑 함께 내가 좋아하는 축구팀이야.",
    },
    {
        "question": "하리가 싫어하는 스포츠가 있어?",
        "answer": "야구는 별로 안 좋아해.",
    },
    {
        "question": "하리는 야구 좋아해?",
        "answer": "아니, 야구는 별로야. 축구가 훨씬 좋아!",
    },
]


def embed_qa(qa_list: list[dict]) -> list[list[float]]:
    """각 Q&A를 임베딩 텍스트로 변환하여 벡터 생성"""
    embeddings_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=OPENAI_API_KEY,
    )
    texts = [
        f"[카테고리: {CATEGORY}]\nQ: {item['question']}\nA: {item['answer']}"
        for item in qa_list
    ]
    vectors = embeddings_model.embed_documents(texts)
    logger.info("임베딩 완료. 벡터 차원: %d", len(vectors[0]) if vectors else 0)
    return vectors


def get_db_connection():
    missing = [k for k, v in {
        "DB_HOST": DB_HOST,
        "DB_USER": DB_USER,
        "DB_PASSWORD": DB_PASSWORD,
    }.items() if not v]
    if missing:
        raise EnvironmentError(f".env에 다음 변수가 누락되어 있습니다: {', '.join(missing)}")
    return psycopg2.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=10,
    )


def insert_rows(conn, qa_list: list[dict], vectors: list[list[float]]) -> None:
    INSERT_SQL = """
        INSERT INTO hari_knowledge (category, question, answer, content_vector, is_active)
        VALUES (%s, %s, %s, %s::vector, TRUE)
        ON CONFLICT DO NOTHING;
    """
    with conn.cursor() as cur:
        for item, vector in zip(qa_list, vectors):
            vector_str = "[" + ",".join(str(v) for v in vector) + "]"
            cur.execute(INSERT_SQL, (
                CATEGORY,
                item["question"],
                item["answer"],
                vector_str,
            ))
            logger.info("삽입: %s", item["question"])
    conn.commit()
    logger.info("총 %d건 삽입 완료.", len(qa_list))


def main():
    parser = argparse.ArgumentParser(description="하리 스포츠 지식 삽입 스크립트")
    parser.add_argument("--dry-run", action="store_true", help="DB 적재 없이 확인만")
    args = parser.parse_args()

    logger.info("삽입할 Q&A %d건:", len(QA_DATA))
    for i, item in enumerate(QA_DATA, 1):
        logger.info("[%d] Q: %s / A: %s", i, item["question"], item["answer"])

    logger.info("임베딩 생성 중...")
    try:
        vectors = embed_qa(QA_DATA)
    except Exception as e:
        logger.error("임베딩 실패: %s", e)
        sys.exit(1)

    if args.dry_run:
        logger.info("[DRY-RUN] 임베딩 성공. DB 적재를 건너뜁니다.")
        return

    try:
        conn = get_db_connection()
    except Exception as e:
        logger.error("DB 연결 실패: %s", e)
        sys.exit(1)

    try:
        insert_rows(conn, QA_DATA, vectors)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM hari_knowledge;")
            count = cur.fetchone()[0]
        logger.info("hari_knowledge 테이블 전체 레코드 수: %d", count)
    except Exception as e:
        logger.error("삽입 중 오류: %s", e)
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
