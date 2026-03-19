# Fix: 채팅 메시지가 DB에 저장되지 않는 문제

## 근본 원인

`chat_messages` 테이블의 `user_id` FK가 **`users.user_id`** (커스텀 테이블)를 참조하고 있지만, Django는 **`auth_user.id`**를 사용합니다.

```
현재:   chat_messages.user_id → users.user_id     ❌
올바른: chat_messages.user_id → auth_user.id       ✅
```

[consumers.py](file:///c:/Workspaces/SKN22-Final-4Team-WEB/backend/chat/consumers.py)에서 `Message.objects.create(user_id=auth_user.id)` 호출 시 FK 위반이 발생하지만, try/except 블록(72-75행)에서 에러가 조용히 무시됩니다.

> [!CAUTION]
> [chat_memory](file:///c:/Workspaces/SKN22-Final-4Team-WEB/backend/chat/consumers.py#142-173) 테이블도 동일한 문제를 가지고 있을 가능성이 높습니다.

## Proposed Changes

### [MODIFY] SQL Migration - FK 재연결

`chat_messages`와 [chat_memory](file:///c:/Workspaces/SKN22-Final-4Team-WEB/backend/chat/consumers.py#142-173)의 FK를 `users` → `auth_user`로 변경하는 새 migration 파일을 생성합니다.

#### [NEW] [0006_fix_fk_to_auth_user.py](file:///c:/Workspaces/SKN22-Final-4Team-WEB/backend/chat/migrations/0006_fix_fk_to_auth_user.py)

```sql
-- chat_messages: FK를 users에서 auth_user로 변경
ALTER TABLE chat_messages DROP CONSTRAINT IF EXISTS chat_messages_user_id_fkey;
ALTER TABLE chat_messages ADD CONSTRAINT chat_messages_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;

-- chat_memory: 동일한 수정 (FK가 있을 경우)
ALTER TABLE chat_memory DROP CONSTRAINT IF EXISTS chat_memory_user_id_fkey;
ALTER TABLE chat_memory ADD CONSTRAINT chat_memory_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
```

## Verification Plan

### Automated Tests
1. `python manage.py migrate` 실행하여 migration 적용
2. 진단 스크립트로 FK가 `auth_user`를 참조하는지 확인
3. Django shell에서 `Message.objects.create()` 테스트
