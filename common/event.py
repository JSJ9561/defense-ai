import ipaddress
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4
from collections.abc import Mapping
from types import MappingProxyType

SCHEMA_VERSION = "1.0"

EVENT_FIELDS = {
    "schema_version",
    "event_id",
    "occurred_at",
    "observed_at",
    "agent_id",
    "host_id",
    "event_type",
    "attributes",
}

AUTH_FIELDS = {"service", "username", "source_ip"}

class EventValidationError(ValueError):
    """보안 이벤트의 데이터 형식이 올바르지 않을 때 발생하는 오류."""

def validate_timestamp(value, field_name, allow_none=False):
    if value is None and allow_none:
        return

    if not isinstance(value, str):
        raise EventValidationError(f"{field_name}: 문자열이 필요합니다.")

    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise EventValidationError(
            f"{field_name}: UTC 시간 형식이 올바르지 않습니다."
        ) from exc

    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise EventValidationError(
            f"{field_name}: YYYY-MM-DDTHH:MM:SSZ 형식이어야 합니다."
        )

def reject_duplicate_keys(pairs):
    result = {}

    for key, value in pairs:
        if key in result:
            raise EventValidationError(
                f"중복된 JSON 필드: {key}"
            )
        result[key] = value

    return result

# 보안 이벤트 데이터 모델
@dataclass(frozen=True)
class SecurityEvent:
    schema_version: str
    event_id: str
    occurred_at: str | None
    observed_at: str
    agent_id: str
    host_id: str
    event_type: str
    attributes: Mapping[str, str]

    def __post_init__(self):
        self.validate()
        object.__setattr__(
            self,
            "attributes",
            MappingProxyType(dict(self.attributes))
        )

    def validate(self):
        if self.schema_version != SCHEMA_VERSION:
            raise EventValidationError("지원하지 않는 스키마 버전입니다.")

        if not isinstance(self.event_id, str):
            raise EventValidationError("event_id는 UUID 문자열이어야 합니다.")

        try:
            parsed_uuid = UUID(self.event_id)
        except (ValueError, TypeError, AttributeError) as exc:
            raise EventValidationError("event_id가 올바르지 않습니다.") from exc

        if parsed_uuid.version != 4 or str(parsed_uuid) != self.event_id:
            raise EventValidationError("event_id는 정규 UUIDv4 형식이어야 합니다.")

        validate_timestamp(self.occurred_at, "occurred_at", allow_none=True)
        validate_timestamp(self.observed_at, "observed_at")

        for field_name in ("agent_id", "host_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise EventValidationError(
                    f"{field_name}: 비어 있지 않은 문자열이어야 합니다."
                )

        if self.event_type != "auth.login_failed":
            raise EventValidationError("지원하지 않는 이벤트 유형입니다.")

        if not isinstance(self.attributes, Mapping):
            raise EventValidationError("attributes는 객체여야 합니다.")

        unknown = set(self.attributes) - AUTH_FIELDS
        if unknown:
            raise EventValidationError(f"허용되지 않는 속성: {sorted(unknown)}")

        service = self.attributes.get("service")
        if not isinstance(service, str) or not service.strip():
            raise EventValidationError("service는 필수 문자열입니다.")

        for name in ("username", "source_ip"):
            if name in self.attributes:
                value = self.attributes[name]
                if not isinstance(value, str) or not value.strip():
                    raise EventValidationError(f"{name} 값이 올바르지 않습니다.")

        if "source_ip" in self.attributes:
            try:
                ipaddress.ip_address(self.attributes["source_ip"])
            except ValueError as exc:
                raise EventValidationError("IP 주소가 올바르지 않습니다.") from exc

    def to_dict(self):
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "occurred_at": self.occurred_at,
            "observed_at": self.observed_at,
            "agent_id": self.agent_id,
            "host_id": self.host_id,
            "event_type": self.event_type,
            "attributes": dict(self.attributes),
        }

    def to_json(self):
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise EventValidationError("이벤트는 JSON 객체여야 합니다.")

        missing = EVENT_FIELDS - set(data)
        extra = set(data) - EVENT_FIELDS

        if missing:
            raise EventValidationError(f"누락된 필드: {sorted(missing)}")
        if extra:
            raise EventValidationError(f"허용되지 않는 필드: {sorted(extra)}")

        return cls(**data)

    @classmethod
    def from_json(cls, text):
        try:
            data = json.loads(
                text,
                object_pairs_hook=reject_duplicate_keys
            )
        except (json.JSONDecodeError, TypeError) as exc:
            raise EventValidationError("올바른 JSON 데이터가 아닙니다.") from exc

        return cls.from_dict(data)

    @classmethod
    def create_login_failure(
        cls, agent_id, host_id, service,
        username=None, source_ip=None, occurred_at=None
    ):
        attributes = {"service": service}

        if username is not None:
            attributes["username"] = username
        if source_ip is not None:
            attributes["source_ip"] = source_ip

        return cls(
            schema_version=SCHEMA_VERSION,
            event_id=str(uuid4()),
            occurred_at=occurred_at,
            observed_at=datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            agent_id=agent_id,
            host_id=host_id,
            event_type="auth.login_failed",
            attributes=attributes,
        )
