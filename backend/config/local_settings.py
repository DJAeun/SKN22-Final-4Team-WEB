# 로컬에서 레디스가 없을 때를 대비해 메모리 채널 레이어 사용
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}
