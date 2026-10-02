import sentry_sdk
from sentry_sdk.integrations.logging import ignore_logger
from sentry_sdk.scrubber import DEFAULT_DENYLIST, EventScrubber

# Thêm vào danh sách mặc định của Sentry (password, token, authorization, cookie...)
# những khóa riêng của dự án: refresh token trong body, chữ ký webhook trong header
EXTRA_DENYLIST = ["refresh", "x-signature", "signature"]


def build_scrubber():
    return EventScrubber(denylist=[*DEFAULT_DENYLIST, *EXTRA_DENYLIST], recursive=True)


def init_sentry(*, dsn, environment, release=None, traces_sample_rate=0.0):
    ignore_logger("django.security.DisallowedHost")   # máy quét internet gõ cửa suốt ngày
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        traces_sample_rate=traces_sample_rate,
        send_default_pii=False,
        event_scrubber=build_scrubber(),
    )