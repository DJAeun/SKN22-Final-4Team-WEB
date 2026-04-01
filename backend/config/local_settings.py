from .settings import *

# 프론트엔드 화면만 빠르게 확인하기 위해, 영구적인 배포용 PostgreSQL DB(배포구조)를 무시하고 
# 내 컴퓨터에 있는 임시 SQLite 파일(db.sqlite3)을 사용하도록 살짝 덮어씌웁니다.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# (마찬가지로 로컬에 레디스가 없을 때를 대비해 메모리 사용으로 우회)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}
