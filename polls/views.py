import json
import re
from datetime import date, datetime, time, timedelta
from functools import wraps
from typing import Any, Dict, List, Optional
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone, translation
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods

from .models import Identity, Poll, PollOption, PollVote

SESSION_IDENTITY_KEY = "identity_id"
VALID_VOTE_STATUSES = {
    PollVote.STATUS_YES,
    PollVote.STATUS_NO,
    PollVote.STATUS_MAYBE,
}
FIXED_SLOT_MINUTES = 60
WEEKDAY_MIN = 0
WEEKDAY_MAX = 6
IDENTIFIER_MAX_LENGTH = 80
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


class APIError(Exception):
    def __init__(self, code: str, status: int = 400, detail: Optional[str] = None) -> None:
        super().__init__(detail or code)
        self.code = code
        self.status = status
        self.detail = detail or code


def api_error_response(exc: APIError) -> JsonResponse:
    return JsonResponse({"error": exc.code, "detail": exc.detail}, status=exc.status)


def parse_json_body(request: HttpRequest) -> Dict[str, Any]:
    if not request.body:
        return {}
    try:
        parsed = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise APIError("invalid_json", 400, "Request body must be valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise APIError("invalid_json", 400, "JSON body must be an object.")
    return parsed


def parse_iso_date(value: Any) -> date:
    if not isinstance(value, str):
        raise APIError("invalid_date", 400, "Date values must be strings in ISO format (YYYY-MM-DD).")
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise APIError("invalid_date", 400, f"Invalid ISO date: {value}") from exc


def poll_start_end_dates(poll: Poll) -> Dict[str, str]:
    # window_ends_at is exclusive; convert to inclusive end-date for UI/API payloads.
    poll_tz = ZoneInfo(poll.timezone_name)
    start_local = timezone.localtime(poll.window_starts_at, poll_tz).date()
    end_inclusive = timezone.localtime(poll.window_ends_at - timedelta(microseconds=1), poll_tz).date()
    return {
        "start_date": start_local.isoformat(),
        "end_date": end_inclusive.isoformat(),
    }


def parse_hour(value: Any, *, field_name: str, min_value: int, max_value: int) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        parsed = value
    elif isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
    else:
        raise APIError("invalid_daily_hours", 400, f"{field_name} must be an integer.")

    if parsed < min_value or parsed > max_value:
        raise APIError(
            "invalid_daily_hours",
            400,
            f"{field_name} must be between {min_value} and {max_value}.",
        )
    return parsed


def parse_allowed_weekdays(value: Any) -> List[int]:
    if not isinstance(value, list):
        raise APIError("invalid_weekdays", 400, "allowed_weekdays must be a list.")

    parsed: List[int] = []
    for item in value:
        if not isinstance(item, int) or isinstance(item, bool):
            raise APIError("invalid_weekdays", 400, "Weekday values must be integers 0-6.")
        if item < WEEKDAY_MIN or item > WEEKDAY_MAX:
            raise APIError("invalid_weekdays", 400, "Weekday values must be between 0 and 6.")
        if item not in parsed:
            parsed.append(item)

    if not parsed:
        raise APIError("invalid_weekdays", 400, "At least one weekday must be selected.")

    parsed.sort()
    return parsed


def validate_timezone_name(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise APIError("invalid_timezone", 400, "timezone must be a non-empty IANA timezone string.")
    timezone_name = value.strip()
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise APIError("invalid_timezone", 400, f"Unsupported timezone: {timezone_name}") from exc
    return timezone_name


def validate_poll_identifier(value: Any) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise APIError(
            "invalid_poll_identifier",
            400,
            "identifier must be text and may contain only A-Z, a-z, 0-9, and underscore.",
        )
    identifier = value.strip()
    if not identifier:
        return None
    if len(identifier) > IDENTIFIER_MAX_LENGTH:
        raise APIError(
            "invalid_poll_identifier",
            400,
            f"identifier cannot exceed {IDENTIFIER_MAX_LENGTH} characters.",
        )
    if not IDENTIFIER_PATTERN.fullmatch(identifier):
        raise APIError(
            "invalid_poll_identifier",
            400,
            "identifier may contain only A-Z, a-z, 0-9, and underscore.",
        )
    return identifier


def poll_reference(poll: Poll) -> str:
    return poll.identifier or str(poll.id)


def get_poll_by_reference(queryset, poll_ref: str) -> Poll:
    normalized = str(poll_ref or "").strip()
    if not normalized:
        raise Http404("No Poll matches the given query.")

    if IDENTIFIER_PATTERN.fullmatch(normalized):
        by_identifier = queryset.filter(identifier=normalized).first()
        if by_identifier is not None:
            return by_identifier

    try:
        parsed_uuid = UUID(normalized)
    except (ValueError, TypeError):
        raise Http404("No Poll matches the given query.")

    by_uuid = queryset.filter(id=parsed_uuid).first()
    if by_uuid is not None:
        return by_uuid
    raise Http404("No Poll matches the given query.")


def parse_poll_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    title = payload.get("title")
    description = payload.get("description", "")
    identifier_raw = payload.get("identifier")
    start_date_raw = payload.get("start_date")
    end_date_raw = payload.get("end_date")
    daily_start_hour_raw = payload.get("daily_start_hour")
    daily_end_hour_raw = payload.get("daily_end_hour")
    allowed_weekdays_raw = payload.get("allowed_weekdays")
    timezone_raw = payload.get("timezone", "UTC")

    if not isinstance(title, str) or not title.strip():
        raise APIError("invalid_title", 400, "Poll title is required.")
    if len(title.strip()) > 160:
        raise APIError("invalid_title", 400, "Poll title cannot exceed 160 characters.")
    if not isinstance(description, str):
        raise APIError("invalid_description", 400, "Description must be text.")
    if len(description) > 1200:
        raise APIError("invalid_description", 400, "Description is too long.")

    start_date = parse_iso_date(start_date_raw)
    end_date = parse_iso_date(end_date_raw)
    if end_date < start_date:
        raise APIError("invalid_date_range", 400, "End date must be on or after start date.")

    daily_start_hour = parse_hour(
        daily_start_hour_raw,
        field_name="daily_start_hour",
        min_value=0,
        max_value=23,
    )
    daily_end_hour = parse_hour(
        daily_end_hour_raw,
        field_name="daily_end_hour",
        min_value=1,
        max_value=24,
    )
    if daily_end_hour <= daily_start_hour:
        raise APIError(
            "invalid_daily_hours",
            400,
            "daily_end_hour must be greater than daily_start_hour.",
        )

    allowed_weekdays = parse_allowed_weekdays(allowed_weekdays_raw)
    timezone_name = validate_timezone_name(timezone_raw)
    identifier = validate_poll_identifier(identifier_raw)

    return {
        "identifier": identifier,
        "title": title.strip(),
        "description": description.strip(),
        "start_date": start_date,
        "end_date": end_date,
        "slot_minutes": FIXED_SLOT_MINUTES,
        "daily_start_hour": daily_start_hour,
        "daily_end_hour": daily_end_hour,
        "allowed_weekdays": allowed_weekdays,
        "timezone_name": timezone_name,
    }


def generate_poll_options(schedule: Dict[str, Any]) -> List[Dict[str, Any]]:
    start_date: date = schedule["start_date"]
    end_date: date = schedule["end_date"]
    daily_start_hour: int = schedule["daily_start_hour"]
    daily_end_hour: int = schedule["daily_end_hour"]
    allowed_weekdays: List[int] = schedule["allowed_weekdays"]
    timezone_name: str = schedule["timezone_name"]

    tz = ZoneInfo(timezone_name)
    parsed_options: List[Dict[str, Any]] = []
    slot_delta = timedelta(minutes=FIXED_SLOT_MINUTES)
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() in allowed_weekdays:
            day_start_at = timezone.make_aware(
                datetime.combine(current_date, time(hour=daily_start_hour)),
                tz,
            )
            if daily_end_hour == 24:
                day_end_at = timezone.make_aware(
                    datetime.combine(current_date + timedelta(days=1), time.min),
                    tz,
                )
            else:
                day_end_at = timezone.make_aware(
                    datetime.combine(current_date, time(hour=daily_end_hour)),
                    tz,
                )

            slot_cursor = day_start_at
            while slot_cursor + slot_delta <= day_end_at:
                parsed_options.append(
                    {
                        "starts_at": slot_cursor,
                        "ends_at": slot_cursor + slot_delta,
                        "label": "",
                    }
                )
                if len(parsed_options) > 2000:
                    raise APIError("too_many_options", 400, "Generated slot count is too high.")
                slot_cursor += slot_delta
        current_date += timedelta(days=1)

    if not parsed_options:
        raise APIError(
            "invalid_options",
            400,
            "No slots were generated. Adjust date range, weekdays or daily hours.",
        )
    return parsed_options


def get_current_identity(request: HttpRequest) -> Optional[Identity]:
    identity_id = request.session.get(SESSION_IDENTITY_KEY)
    if not identity_id:
        return None

    if hasattr(request, "_cached_identity"):
        return request._cached_identity

    try:
        identity = Identity.objects.get(id=identity_id)
    except Identity.DoesNotExist:
        request.session.pop(SESSION_IDENTITY_KEY, None)
        request._cached_identity = None
        return None

    request._cached_identity = identity
    return identity


def authenticate_request(view_func):
    @wraps(view_func)
    def wrapped(request: HttpRequest, *args, **kwargs):
        identity = get_current_identity(request)
        if identity is None:
            return JsonResponse(
                {"error": "authentication_required", "detail": "Login is required for this action."},
                status=401,
            )
        request.identity = identity
        return view_func(request, *args, **kwargs)

    return wrapped


def validate_name(name: Any) -> str:
    if not isinstance(name, str):
        raise APIError("invalid_name", 400, "Name must be text.")

    cleaned = name.strip()
    if len(cleaned) < 2:
        raise APIError("invalid_name", 400, "Name must be at least 2 characters long.")
    if len(cleaned) > 80:
        raise APIError("invalid_name", 400, "Name cannot be longer than 80 characters.")

    return cleaned


def validate_pin(pin: Any) -> str:
    if not isinstance(pin, str):
        raise APIError("invalid_pin", 400, "PIN must be a string of digits.")

    cleaned = pin.strip()
    if not cleaned.isdigit() or not (4 <= len(cleaned) <= 12):
        raise APIError("invalid_pin", 400, "PIN must contain 4-12 digits.")

    return cleaned


def serialize_identity(identity: Identity) -> Dict[str, Any]:
    return {
        "id": identity.id,
        "name": identity.name,
    }


def serialize_identity_full(identity: Identity) -> Dict[str, Any]:
    return {
        "id": identity.id,
        "name": identity.name,
        "created_at": identity.created_at.isoformat(),
        "updated_at": identity.updated_at.isoformat(),
    }


def serialize_identity_data_export(identity: Identity) -> Dict[str, Any]:
    created_polls = (
        Poll.objects.filter(creator=identity)
        .select_related("creator")
        .prefetch_related("options__votes__voter")
    )
    votes = (
        PollVote.objects.filter(voter=identity)
        .select_related("poll_option__poll", "poll_option__poll__creator")
        .order_by("created_at")
    )

    votes_payload: List[Dict[str, Any]] = []
    vote_poll_ids = set()
    for vote in votes:
        poll = vote.poll_option.poll
        vote_poll_ids.add(poll.id)
        votes_payload.append(
            {
                "id": vote.id,
                "poll_id": poll_reference(poll),
                "poll_title": poll.title,
                "poll_is_closed": poll.is_closed,
                "poll_option_id": vote.poll_option_id,
                "option_starts_at": vote.poll_option.starts_at.isoformat(),
                "option_ends_at": vote.poll_option.ends_at.isoformat() if vote.poll_option.ends_at else None,
                "status": vote.status,
                "created_at": vote.created_at.isoformat(),
                "updated_at": vote.updated_at.isoformat(),
            }
        )

    created_poll_payload = [serialize_poll_detail(poll, identity) for poll in created_polls]
    return {
        "identity": serialize_identity_full(identity),
        "created_polls": created_poll_payload,
        "votes": votes_payload,
        "stats": {
            "created_poll_count": len(created_poll_payload),
            "vote_count": len(votes_payload),
            "distinct_poll_count_voted": len(vote_poll_ids),
        },
    }


def serialize_poll_summary(poll: Poll, current_identity: Optional[Identity]) -> Dict[str, Any]:
    participant_ids = set()
    option_count = 0
    my_vote_count = 0

    for option in poll.options.all():
        option_count += 1
        for vote in option.votes.all():
            participant_ids.add(vote.voter_id)
            if current_identity and vote.voter_id == current_identity.id:
                my_vote_count += 1

    date_window = poll_start_end_dates(poll)
    return {
        "id": poll_reference(poll),
        "identifier": poll.identifier,
        "title": poll.title,
        "description": poll.description,
        "window_starts_at": poll.window_starts_at.isoformat(),
        "window_ends_at": poll.window_ends_at.isoformat(),
        "start_date": date_window["start_date"],
        "end_date": date_window["end_date"],
        "slot_minutes": poll.slot_minutes,
        "daily_start_hour": poll.daily_start_hour,
        "daily_end_hour": poll.daily_end_hour,
        "allowed_weekdays": poll.allowed_weekdays,
        "timezone": poll.timezone_name,
        "is_closed": poll.is_closed,
        "created_at": poll.created_at.isoformat(),
        "closed_at": poll.closed_at.isoformat() if poll.closed_at else None,
        "creator": serialize_identity(poll.creator),
        "option_count": option_count,
        "participant_count": len(participant_ids),
        "my_vote_count": my_vote_count,
        "can_close": bool(current_identity and poll.creator_id == current_identity.id and not poll.is_closed),
        "can_reopen": bool(current_identity and poll.creator_id == current_identity.id and poll.is_closed),
        "can_delete": bool(current_identity and poll.creator_id == current_identity.id and poll.is_closed),
        "can_edit": bool(current_identity and poll.creator_id == current_identity.id and not poll.is_closed),
    }


def serialize_poll_detail(poll: Poll, current_identity: Optional[Identity]) -> Dict[str, Any]:
    participant_ids = set()
    options_payload: List[Dict[str, Any]] = []

    for option in poll.options.all():
        my_vote = None
        status_counts = {
            PollVote.STATUS_YES: 0,
            PollVote.STATUS_NO: 0,
            PollVote.STATUS_MAYBE: 0,
        }

        for vote in option.votes.all():
            participant_ids.add(vote.voter_id)
            if vote.status in status_counts:
                status_counts[vote.status] += 1
            if current_identity and vote.voter_id == current_identity.id:
                my_vote = vote.status

        options_payload.append(
            {
                "id": option.id,
                "label": option.label,
                "starts_at": option.starts_at.isoformat(),
                "ends_at": option.ends_at.isoformat() if option.ends_at else None,
                "counts": status_counts,
                "yes_count": status_counts[PollVote.STATUS_YES],
                "my_vote": my_vote,
            }
        )

    date_window = poll_start_end_dates(poll)
    return {
        "id": poll_reference(poll),
        "identifier": poll.identifier,
        "title": poll.title,
        "description": poll.description,
        "window_starts_at": poll.window_starts_at.isoformat(),
        "window_ends_at": poll.window_ends_at.isoformat(),
        "start_date": date_window["start_date"],
        "end_date": date_window["end_date"],
        "slot_minutes": poll.slot_minutes,
        "daily_start_hour": poll.daily_start_hour,
        "daily_end_hour": poll.daily_end_hour,
        "allowed_weekdays": poll.allowed_weekdays,
        "timezone": poll.timezone_name,
        "is_closed": poll.is_closed,
        "created_at": poll.created_at.isoformat(),
        "closed_at": poll.closed_at.isoformat() if poll.closed_at else None,
        "creator": serialize_identity(poll.creator),
        "options": options_payload,
        "participant_count": len(participant_ids),
        "can_vote": bool(current_identity and not poll.is_closed),
        "can_close": bool(current_identity and poll.creator_id == current_identity.id and not poll.is_closed),
        "can_reopen": bool(current_identity and poll.creator_id == current_identity.id and poll.is_closed),
        "can_delete": bool(current_identity and poll.creator_id == current_identity.id and poll.is_closed),
        "can_edit": bool(current_identity and poll.creator_id == current_identity.id and not poll.is_closed),
    }


@ensure_csrf_cookie
@require_GET
def index(request: HttpRequest) -> HttpResponse:
    return render(request, "polls/index.html")


@require_GET
def auth_session(request: HttpRequest) -> JsonResponse:
    identity = get_current_identity(request)
    language = translation.get_language_from_request(request)
    return JsonResponse(
        {
            "authenticated": bool(identity),
            "identity": serialize_identity(identity) if identity else None,
            "language": language,
        }
    )


@require_http_methods(["POST"])
def register_identity(request: HttpRequest) -> JsonResponse:
    try:
        payload = parse_json_body(request)
        name = validate_name(payload.get("name"))
        pin = validate_pin(payload.get("pin"))
        name_key = Identity.build_name_key(name)

        if Identity.objects.filter(name_key=name_key).exists():
            raise APIError("name_taken", 409, "This name is already registered.")

        identity = Identity(name=name, name_key=name_key)
        identity.set_pin(pin)
        try:
            identity.save()
        except IntegrityError as exc:
            raise APIError("name_taken", 409, "This name is already registered.") from exc

        request.session[SESSION_IDENTITY_KEY] = identity.id
        request._cached_identity = identity

        return JsonResponse({"authenticated": True, "identity": serialize_identity(identity)}, status=201)
    except APIError as exc:
        return api_error_response(exc)


@require_http_methods(["POST"])
def login_identity(request: HttpRequest) -> JsonResponse:
    try:
        payload = parse_json_body(request)
        name = validate_name(payload.get("name"))
        pin = validate_pin(payload.get("pin"))
        name_key = Identity.build_name_key(name)

        created = False
        identity = Identity.objects.filter(name_key=name_key).first()
        if identity is None:
            identity = Identity(name=name, name_key=name_key)
            identity.set_pin(pin)
            try:
                identity.save()
                created = True
            except IntegrityError:
                identity = Identity.objects.filter(name_key=name_key).first()
                if identity is None:
                    raise APIError("invalid_credentials", 401, "Incorrect name or PIN.")
                if not identity.check_pin(pin):
                    raise APIError("invalid_credentials", 401, "Incorrect name or PIN.")
        elif not identity.check_pin(pin):
            raise APIError("invalid_credentials", 401, "Incorrect name or PIN.")

        request.session[SESSION_IDENTITY_KEY] = identity.id
        request._cached_identity = identity

        return JsonResponse(
            {"authenticated": True, "identity": serialize_identity(identity), "created": created},
            status=201 if created else 200,
        )
    except APIError as exc:
        return api_error_response(exc)


@require_http_methods(["POST"])
def logout_identity(request: HttpRequest) -> JsonResponse:
    request.session.flush()
    request._cached_identity = None
    return JsonResponse({"authenticated": False})


@require_http_methods(["GET", "DELETE"])
@authenticate_request
def auth_me_data(request: HttpRequest) -> JsonResponse:
    identity = request.identity

    if request.method == "GET":
        return JsonResponse(serialize_identity_data_export(identity))

    created_poll_ids = list(
        Poll.objects.filter(creator=identity).values_list("id", flat=True)
    )
    polls_with_other_votes = set(
        PollVote.objects.filter(poll_option__poll__creator=identity)
        .exclude(voter=identity)
        .values_list("poll_option__poll_id", flat=True)
        .distinct()
    )
    deletable_poll_ids = [poll_id for poll_id in created_poll_ids if poll_id not in polls_with_other_votes]

    remaining_created_with_other_votes = list(
        Poll.objects.filter(id__in=polls_with_other_votes, creator=identity)
        .values("id", "identifier", "title", "is_closed")
    )
    for item in remaining_created_with_other_votes:
        item["id"] = item["identifier"] or str(item["id"])
        item.pop("identifier", None)

    with transaction.atomic():
        deleted_votes_count, _ = PollVote.objects.filter(voter=identity).delete()

        deletable_qs = Poll.objects.filter(id__in=deletable_poll_ids, creator=identity)
        deleted_polls_count = deletable_qs.count()
        if deleted_polls_count:
            deletable_qs.delete()

        remaining_created_polls_count = Poll.objects.filter(creator=identity).count()
        remaining_votes_count = PollVote.objects.filter(voter=identity).count()

        deleted_identity = False
        if remaining_created_polls_count == 0 and remaining_votes_count == 0:
            identity.delete()
            deleted_identity = True

    if deleted_identity:
        request.session.pop(SESSION_IDENTITY_KEY, None)
        request._cached_identity = None
        identity_payload = None
    else:
        request._cached_identity = identity
        identity_payload = serialize_identity(identity)

    return JsonResponse(
        {
            "deleted_votes_count": deleted_votes_count,
            "deleted_polls_count": deleted_polls_count,
            "remaining_created_polls_count": remaining_created_polls_count,
            "remaining_created_polls_with_other_votes": remaining_created_with_other_votes,
            "deleted_identity": deleted_identity,
            "identity": identity_payload,
        }
    )


@require_http_methods(["POST"])
def set_language_view(request: HttpRequest) -> JsonResponse:
    try:
        payload = parse_json_body(request)
        language = payload.get("language")
        allowed = {code for code, _label in settings.LANGUAGES}
        if language not in allowed:
            raise APIError("invalid_language", 400, "Unsupported language code.")

        translation.activate(language)

        response = JsonResponse({"language": language})
        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME,
            language,
            max_age=settings.LANGUAGE_COOKIE_AGE,
            path=settings.LANGUAGE_COOKIE_PATH,
            domain=settings.LANGUAGE_COOKIE_DOMAIN,
            secure=settings.LANGUAGE_COOKIE_SECURE,
            httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
            samesite=settings.LANGUAGE_COOKIE_SAMESITE,
        )
        return response
    except APIError as exc:
        return api_error_response(exc)


@require_http_methods(["GET", "POST"])
def polls_collection(request: HttpRequest) -> JsonResponse:
    current_identity = get_current_identity(request)

    if request.method == "GET":
        polls = (
            Poll.objects.select_related("creator")
            .prefetch_related("options__votes")
            .all()
        )
        polls_payload = [serialize_poll_summary(poll, current_identity) for poll in polls]
        return JsonResponse({"polls": polls_payload})

    if current_identity is None:
        return JsonResponse(
            {"error": "authentication_required", "detail": "Login is required for this action."},
            status=401,
        )

    try:
        request_payload = parse_json_body(request)
        schedule = parse_poll_payload(request_payload)
        if schedule["identifier"] and Poll.objects.filter(identifier=schedule["identifier"]).exists():
            raise APIError("poll_identifier_taken", 409, "This identifier is already in use.")
        parsed_options = generate_poll_options(schedule)
        tz = ZoneInfo(schedule["timezone_name"])
        window_starts_at = datetime.combine(schedule["start_date"], time.min, tzinfo=tz)
        window_ends_at = datetime.combine(schedule["end_date"] + timedelta(days=1), time.min, tzinfo=tz)

        with transaction.atomic():
            poll = Poll.objects.create(
                creator=current_identity,
                identifier=schedule["identifier"],
                title=schedule["title"],
                description=schedule["description"],
                window_starts_at=window_starts_at,
                window_ends_at=window_ends_at,
                slot_minutes=schedule["slot_minutes"],
                daily_start_hour=schedule["daily_start_hour"],
                daily_end_hour=schedule["daily_end_hour"],
                allowed_weekdays=schedule["allowed_weekdays"],
                timezone_name=schedule["timezone_name"],
            )
            PollOption.objects.bulk_create(
                [
                    PollOption(
                        poll=poll,
                        starts_at=item["starts_at"],
                        ends_at=item["ends_at"],
                        label=item["label"],
                    )
                    for item in parsed_options
                ]
            )

        poll = (
            Poll.objects.select_related("creator")
            .prefetch_related("options__votes__voter")
            .get(id=poll.id)
        )
        return JsonResponse({"poll": serialize_poll_detail(poll, current_identity)}, status=201)
    except APIError as exc:
        return api_error_response(exc)
    except IntegrityError:
        return api_error_response(APIError("poll_identifier_taken", 409, "This identifier is already in use."))


@require_http_methods(["GET", "DELETE", "PUT"])
def poll_detail(request: HttpRequest, poll_ref: str) -> JsonResponse:
    current_identity = get_current_identity(request)
    poll = get_poll_by_reference(
        Poll.objects.select_related("creator").prefetch_related("options__votes__voter"),
        poll_ref,
    )

    if request.method == "GET":
        return JsonResponse({"poll": serialize_poll_detail(poll, current_identity)})

    if request.method == "PUT":
        if current_identity is None:
            return JsonResponse(
                {"error": "authentication_required", "detail": "Login is required for this action."},
                status=401,
            )

        if poll.creator_id != current_identity.id:
            return JsonResponse({"error": "forbidden", "detail": "Only the poll creator can edit this poll."}, status=403)
        if poll.is_closed:
            return JsonResponse({"error": "poll_closed", "detail": "Closed polls cannot be edited."}, status=409)

        try:
            payload = parse_json_body(request)
            schedule = parse_poll_payload(payload)
            if schedule["identifier"] and Poll.objects.filter(identifier=schedule["identifier"]).exclude(id=poll.id).exists():
                raise APIError("poll_identifier_taken", 409, "This identifier is already in use.")
            generated_options = generate_poll_options(schedule)
            tz = ZoneInfo(schedule["timezone_name"])
            window_starts_at = datetime.combine(schedule["start_date"], time.min, tzinfo=tz)
            window_ends_at = datetime.combine(schedule["end_date"] + timedelta(days=1), time.min, tzinfo=tz)

            desired_keys = {(item["starts_at"], item["ends_at"]) for item in generated_options}

            option_qs = poll.options.all().prefetch_related("votes")
            voted_options = [option for option in option_qs if bool(option.votes.all())]
            voted_outside_new_range = [
                option for option in voted_options if (option.starts_at, option.ends_at) not in desired_keys
            ]
            if voted_outside_new_range:
                raise APIError(
                    "schedule_conflicts_with_votes",
                    409,
                    "Cannot remove or shrink time slots that already have votes.",
                )

            with transaction.atomic():
                poll.identifier = schedule["identifier"]
                poll.title = schedule["title"]
                poll.description = schedule["description"]
                poll.window_starts_at = window_starts_at
                poll.window_ends_at = window_ends_at
                poll.slot_minutes = schedule["slot_minutes"]
                poll.daily_start_hour = schedule["daily_start_hour"]
                poll.daily_end_hour = schedule["daily_end_hour"]
                poll.allowed_weekdays = schedule["allowed_weekdays"]
                poll.timezone_name = schedule["timezone_name"]
                poll.save(
                    update_fields=[
                        "identifier",
                        "title",
                        "description",
                        "window_starts_at",
                        "window_ends_at",
                        "slot_minutes",
                        "daily_start_hour",
                        "daily_end_hour",
                        "allowed_weekdays",
                        "timezone_name",
                    ]
                )

                existing_by_key = {(option.starts_at, option.ends_at): option for option in option_qs}
                desired_key_set = set(desired_keys)

                create_items = [
                    item for item in generated_options if (item["starts_at"], item["ends_at"]) not in existing_by_key
                ]
                if create_items:
                    PollOption.objects.bulk_create(
                        [
                            PollOption(
                                poll=poll,
                                starts_at=item["starts_at"],
                                ends_at=item["ends_at"],
                                label=item["label"],
                            )
                            for item in create_items
                        ]
                    )

                remove_option_ids = [
                    option.id
                    for key, option in existing_by_key.items()
                    if key not in desired_key_set and not bool(option.votes.all())
                ]
                if remove_option_ids:
                    PollOption.objects.filter(id__in=remove_option_ids).delete()

            refreshed = (
                Poll.objects.select_related("creator")
                .prefetch_related("options__votes__voter")
                .get(id=poll.id)
            )
            return JsonResponse({"poll": serialize_poll_detail(refreshed, current_identity)})
        except APIError as exc:
            return api_error_response(exc)
        except IntegrityError:
            return api_error_response(APIError("poll_identifier_taken", 409, "This identifier is already in use."))

    if current_identity is None:
        return JsonResponse(
            {"error": "authentication_required", "detail": "Login is required for this action."},
            status=401,
        )

    if poll.creator_id != current_identity.id:
        return JsonResponse({"error": "forbidden", "detail": "Only the poll creator can delete this poll."}, status=403)
    if not poll.is_closed:
        return JsonResponse(
            {"error": "poll_not_closed", "detail": "Close the poll before deleting it."},
            status=409,
        )

    poll.delete()
    return JsonResponse({"deleted": True})


@require_http_methods(["POST"])
@authenticate_request
def poll_close(request: HttpRequest, poll_ref: str) -> JsonResponse:
    poll = get_poll_by_reference(Poll.objects.select_related("creator"), poll_ref)

    if poll.creator_id != request.identity.id:
        return JsonResponse({"error": "forbidden", "detail": "Only the poll creator can close this poll."}, status=403)

    if not poll.is_closed:
        poll.is_closed = True
        poll.closed_at = timezone.now()
        poll.save(update_fields=["is_closed", "closed_at"])

    poll = (
        Poll.objects.select_related("creator")
        .prefetch_related("options__votes__voter")
        .get(id=poll.id)
    )
    return JsonResponse({"poll": serialize_poll_detail(poll, request.identity)})


@require_http_methods(["POST"])
@authenticate_request
def poll_reopen(request: HttpRequest, poll_ref: str) -> JsonResponse:
    poll = get_poll_by_reference(Poll.objects.select_related("creator"), poll_ref)

    if poll.creator_id != request.identity.id:
        return JsonResponse({"error": "forbidden", "detail": "Only the poll creator can reopen this poll."}, status=403)

    if poll.is_closed:
        poll.is_closed = False
        poll.closed_at = None
        poll.save(update_fields=["is_closed", "closed_at"])

    poll = (
        Poll.objects.select_related("creator")
        .prefetch_related("options__votes__voter")
        .get(id=poll.id)
    )
    return JsonResponse({"poll": serialize_poll_detail(poll, request.identity)})


@require_http_methods(["PUT"])
@authenticate_request
def poll_votes_upsert(request: HttpRequest, poll_ref: str) -> JsonResponse:
    poll = get_poll_by_reference(
        Poll.objects.select_related("creator").prefetch_related("options"),
        poll_ref,
    )

    if poll.is_closed:
        return JsonResponse({"error": "poll_closed", "detail": "Votes cannot be changed after poll closure."}, status=409)

    try:
        payload = parse_json_body(request)
        votes_payload = payload.get("votes")
        if not isinstance(votes_payload, list) or not votes_payload:
            raise APIError("invalid_votes", 400, "Votes payload must be a non-empty list.")

        option_map = {option.id: option for option in poll.options.all()}

        with transaction.atomic():
            for vote in votes_payload:
                if not isinstance(vote, dict):
                    raise APIError("invalid_votes", 400, "Each vote must be an object.")

                option_id = vote.get("option_id")
                if not isinstance(option_id, int) or option_id not in option_map:
                    raise APIError("invalid_votes", 400, "Vote option does not belong to this poll.")

                status = vote.get("status")
                if status in ("", None):
                    PollVote.objects.filter(
                        poll_option=option_map[option_id],
                        voter=request.identity,
                    ).delete()
                    continue

                if not isinstance(status, str) or status not in VALID_VOTE_STATUSES:
                    raise APIError("invalid_votes", 400, "Vote status must be yes, no, maybe or empty.")

                PollVote.objects.update_or_create(
                    poll_option=option_map[option_id],
                    voter=request.identity,
                    defaults={"status": status},
                )

        refreshed = (
            Poll.objects.select_related("creator")
            .prefetch_related("options__votes__voter")
            .get(id=poll.id)
        )
        return JsonResponse({"poll": serialize_poll_detail(refreshed, request.identity)})
    except APIError as exc:
        return api_error_response(exc)


@require_http_methods(["DELETE"])
@authenticate_request
def poll_vote_delete(request: HttpRequest, poll_ref: str, option_id: int) -> JsonResponse:
    poll = get_poll_by_reference(Poll.objects.only("id", "identifier", "is_closed"), poll_ref)

    if poll.is_closed:
        return JsonResponse({"error": "poll_closed", "detail": "Votes cannot be changed after poll closure."}, status=409)

    option = get_object_or_404(PollOption, id=option_id, poll_id=poll.id)
    deleted, _ = PollVote.objects.filter(poll_option=option, voter=request.identity).delete()
    return JsonResponse({"deleted": bool(deleted)})
