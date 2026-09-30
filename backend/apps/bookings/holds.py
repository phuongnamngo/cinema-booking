from functools import lru_cache

import redis
from django.conf import settings

# KEYS = các key hold; ARGV[1] = owner; ARGV[2] = TTL (giây)
# Trả 0 nếu giữ được tất cả, ngược lại trả vị trí (bắt đầu từ 1) của key đang bị người khác giữ
ACQUIRE_LUA = """
for i, key in ipairs(KEYS) do
  local holder = redis.call('GET', key)
  if holder and holder ~= ARGV[1] then
    return i
  end
end
for _, key in ipairs(KEYS) do
  redis.call('SET', key, ARGV[1], 'EX', ARGV[2])
end
return 0
"""

# Chỉ xóa key nếu vẫn thuộc về owner (compare-and-delete)
RELEASE_LUA = """
local n = 0
for _, key in ipairs(KEYS) do
  if redis.call('GET', key) == ARGV[1] then
    redis.call('DEL', key)
    n = n + 1
  end
end
return n
"""


@lru_cache(maxsize=None)
def _client(url):
    return redis.Redis.from_url(url, decode_responses=True)


def get_redis():
    return _client(settings.REDIS_URL)


def hold_key(showtime_id, seat_id):
    return f"hold:{showtime_id}:{seat_id}"


def acquire_holds(showtime_id, seat_ids, owner, ttl):
    """Giữ tất cả ghế hoặc không ghế nào.

    Trả về seat_id đang bị người khác giữ, hoặc None nếu giữ thành công.
    """
    keys = [hold_key(showtime_id, s) for s in seat_ids]
    result = get_redis().eval(ACQUIRE_LUA, len(keys), *keys, owner, ttl)
    return seat_ids[result - 1] if result else None


def release_holds(showtime_id, seat_ids, owner):
    keys = [hold_key(showtime_id, s) for s in seat_ids]
    return get_redis().eval(RELEASE_LUA, len(keys), *keys, owner)