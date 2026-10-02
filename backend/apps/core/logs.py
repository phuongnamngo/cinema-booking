import contextvars
import json
import logging
import time

# Mỗi request (kể cả khi chạy đồng thời) có giá trị riêng. "-" = log ngoài request (Celery, khởi động)
request_id_var = contextvars.ContextVar("request_id", default="-")

# Thuộc tính có sẵn của LogRecord: thứ gì ngoài danh sách này là "extra" do code truyền vào
_RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
    "message", "asctime", "request_id",
}


class RequestIdFilter(logging.Filter):
    """Gắn request_id vào mọi bản ghi. Phải gắn vào HANDLER, không phải logger: filter của logger
    chỉ áp dụng cho record do chính nó phát ra, không áp dụng cho record từ logger con truyền lên."""

    def filter(self, record):
        record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """Mỗi bản ghi = đúng một dòng JSON (xuống dòng trong message được json.dumps escape)."""

    converter = time.gmtime   # log luôn theo UTC

    def format(self, record):
        payload = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)