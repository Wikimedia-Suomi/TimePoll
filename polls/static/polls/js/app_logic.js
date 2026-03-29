(() => {
  function extractPollIdFromSearch(search) {
    try {
      const params = new URLSearchParams(String(search || ""));
      return String(params.get("id") || "").trim();
    } catch (_error) {
      return "";
    }
  }

  function buildPollUrlState(currentHref, pollId) {
    const normalizedPollId = String(pollId || "").trim();
    const url = new URL(String(currentHref || "/"), "https://timepoll.local");

    if (normalizedPollId) {
      url.searchParams.set("id", normalizedPollId);
    } else {
      url.searchParams.delete("id");
    }

    return {
      normalizedPollId,
      nextUrl: `${url.pathname}${url.search}${url.hash}`
    };
  }

  function isVoteStatusValue(status) {
    return status === "yes" || status === "no" || status === "maybe";
  }

  function nextVoteStatus(currentStatus, selectedStatus) {
    if (!isVoteStatusValue(selectedStatus)) {
      return "";
    }
    return currentStatus === selectedStatus ? "" : selectedStatus;
  }

  function readOptionCount(option, status) {
    if (!option || !option.counts) {
      return 0;
    }
    const count = Number(option.counts[status]);
    return Number.isNaN(count) ? 0 : count;
  }

  function matchesYesVoteFilter(option, minYesVotes) {
    if (!option || typeof option !== "object") {
      return false;
    }
    return readOptionCount(option, "yes") >= Math.max(0, Number(minYesVotes) || 0);
  }

  function filterWeekRowsByMinYesVotes(week, minYesVotes) {
    if (!week || !Array.isArray(week.rows)) {
      return [];
    }
    return filterRowsForVisibleDaysAndMinYesVotes(week.rows, null, minYesVotes);
  }

  function filterRowsForVisibleDaysAndMinYesVotes(rows, visibleDayKeys, minYesVotes) {
    if (!Array.isArray(rows)) {
      return [];
    }

    const normalizedMinYesVotes = Math.max(0, Number(minYesVotes) || 0);
    const normalizedVisibleDayKeys = Array.isArray(visibleDayKeys) && visibleDayKeys.length
      ? visibleDayKeys
          .map((dayKey) => String(dayKey || "").trim())
          .filter((dayKey) => Boolean(dayKey))
      : null;
    const filteredRows = [];
    for (const row of rows) {
      if (!row || !row.cells || typeof row.cells !== "object") {
        continue;
      }
      const targetDayKeys = normalizedVisibleDayKeys || Object.keys(row.cells);
      const filteredCells = {};
      for (const dayKey of targetDayKeys) {
        const option = row.cells[dayKey];
        if (!option || typeof option !== "object") {
          continue;
        }
        if (normalizedMinYesVotes <= 0 || matchesYesVoteFilter(option, normalizedMinYesVotes)) {
          filteredCells[dayKey] = option;
        }
      }
      if (Object.keys(filteredCells).length > 0) {
        filteredRows.push({
          ...row,
          cells: filteredCells
        });
      }
    }
    return filteredRows;
  }

  function collectDayOptionIdsFromRows(rows, dayKey) {
    if (!Array.isArray(rows)) {
      return [];
    }
    const optionIds = [];
    for (const row of rows) {
      const option = row && row.cells ? row.cells[dayKey] : null;
      if (option && Number.isInteger(option.id)) {
        optionIds.push(option.id);
      }
    }
    return optionIds;
  }

  function collectRowOptionIdsFromCells(row, dayKeys) {
    if (!row || !row.cells || typeof row.cells !== "object") {
      return [];
    }
    const targetDayKeys = Array.isArray(dayKeys) && dayKeys.length ? dayKeys : Object.keys(row.cells);
    const optionIds = [];
    for (const dayKey of targetDayKeys) {
      const option = row.cells[dayKey];
      if (option && Number.isInteger(option.id)) {
        optionIds.push(option.id);
      }
    }
    return optionIds;
  }

  function toggleWeekdaySelection(values, weekday) {
    if (!Array.isArray(values)) {
      return [];
    }

    const normalizedValues = values
      .map((value) => Number(value))
      .filter((value) => Number.isInteger(value) && value >= 0 && value <= 6);
    const nextValues = Array.from(new Set(normalizedValues));
    const normalizedWeekday = Number(weekday);

    if (!Number.isInteger(normalizedWeekday) || normalizedWeekday < 0 || normalizedWeekday > 6) {
      return [...nextValues].sort((left, right) => left - right);
    }

    const existingIndex = nextValues.indexOf(normalizedWeekday);
    if (existingIndex >= 0) {
      nextValues.splice(existingIndex, 1);
    } else {
      nextValues.push(normalizedWeekday);
    }

    nextValues.sort((left, right) => left - right);
    return nextValues;
  }

  function normalizeIsoDayKey(value) {
    const raw = String(value || "").trim();
    return /^\d{4}-\d{2}-\d{2}$/.test(raw) ? raw : "";
  }

  function normalizeHourValue(value, minValue, maxValue) {
    const normalized = Number(value);
    if (!Number.isInteger(normalized) || normalized < minValue || normalized > maxValue) {
      return null;
    }
    return normalized;
  }

  function normalizeWeekdayValues(values) {
    if (!Array.isArray(values)) {
      return [];
    }
    return Array.from(
      new Set(
        values
          .map((value) => Number(value))
          .filter((value) => Number.isInteger(value) && value >= 0 && value <= 6)
      )
    ).sort((left, right) => left - right);
  }

  function isValidTimeZoneName(value) {
    if (typeof value !== "string" || !value.trim()) {
      return false;
    }
    try {
      new Intl.DateTimeFormat("en-US", { timeZone: value.trim() }).format(new Date());
      return true;
    } catch (_error) {
      return false;
    }
  }

  function parseIsoDateValue(value) {
    if (typeof value !== "string") {
      return null;
    }
    const trimmed = value.trim();
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(trimmed);
    if (!match) {
      return null;
    }
    const year = Number(match[1]);
    const month = Number(match[2]);
    const day = Number(match[3]);
    const parsed = new Date(Date.UTC(year, month - 1, day));
    if (
      parsed.getUTCFullYear() !== year ||
      parsed.getUTCMonth() + 1 !== month ||
      parsed.getUTCDate() !== day
    ) {
      return null;
    }
    return parsed;
  }

  const pollFormBackendErrorFieldMap = {
    invalid_title: ["title"],
    invalid_poll_identifier: ["identifier"],
    poll_identifier_taken: ["identifier"],
    invalid_timezone: ["timezone"],
    invalid_date_range: ["start_date", "end_date"],
    invalid_date: ["start_date", "end_date"],
    invalid_daily_hours: ["daily_start_hour", "daily_end_hour"],
    invalid_weekdays: ["allowed_weekdays"],
    too_many_options: ["start_date", "end_date", "daily_start_hour", "daily_end_hour", "allowed_weekdays"],
    schedule_conflicts_with_votes: [
      "timezone",
      "start_date",
      "end_date",
      "daily_start_hour",
      "daily_end_hour",
      "allowed_weekdays"
    ]
  };

  function createPollFormValidator({
    fieldValidationMessage,
    hasScheduleConflictWithVotes,
    resolveError
  } = {}) {
    const resolveFieldValidationMessage =
      typeof fieldValidationMessage === "function"
        ? fieldValidationMessage
        : (_context, _fieldKey, _kind) => "";
    const resolveFieldError =
      typeof resolveError === "function"
        ? resolveError
        : (_context, payload, fallback) => fallback || String(payload && payload.error || "");
    const checkScheduleConflict =
      typeof hasScheduleConflictWithVotes === "function"
        ? hasScheduleConflictWithVotes
        : () => false;

    return {
      backendErrorFields(errorCode) {
        return Array.isArray(pollFormBackendErrorFieldMap[errorCode])
          ? [...pollFormBackendErrorFieldMap[errorCode]]
          : [];
      },
      buildErrors(context, form, options = {}) {
        const scope = options.scope === "edit" ? "edit" : "create";
        const errors = {};
        if (!form || typeof form !== "object") {
          return errors;
        }

        const title = String(form.title || "").trim();
        const identifier = String(form.identifier || "").trim();
        const startDateRaw = String(form.start_date || "").trim();
        const endDateRaw = String(form.end_date || "").trim();
        const timezoneName = String(form.timezone || "").trim();

        if (!title) {
          errors.title = resolveFieldValidationMessage(context, "title", "required");
        } else if (title.length > 160) {
          errors.title = resolveFieldValidationMessage(context, "title", "tooLong");
        }

        if (identifier && (identifier.length > 80 || !/^[A-Za-z0-9_]+$/.test(identifier))) {
          errors.identifier = resolveFieldError(context, { error: "invalid_poll_identifier" }, "");
        }

        const startDate = parseIsoDateValue(startDateRaw);
        const endDate = parseIsoDateValue(endDateRaw);

        if (!startDateRaw) {
          errors.start_date = resolveFieldValidationMessage(context, "startDate", "required");
        } else if (!startDate) {
          errors.start_date = resolveFieldError(
            context,
            { error: "invalid_date" },
            resolveFieldValidationMessage(context, "startDate", "invalid")
          );
        }

        if (!endDateRaw) {
          errors.end_date = resolveFieldValidationMessage(context, "endDate", "required");
        } else if (!endDate) {
          errors.end_date = resolveFieldError(
            context,
            { error: "invalid_date" },
            resolveFieldValidationMessage(context, "endDate", "invalid")
          );
        }

        if (startDate && endDate && endDate.getTime() < startDate.getTime()) {
          const rangeError = resolveFieldError(context, { error: "invalid_date_range" }, "");
          errors.start_date = rangeError;
          errors.end_date = rangeError;
        }

        if (!Number.isInteger(form.daily_start_hour)) {
          errors.daily_start_hour = resolveFieldValidationMessage(context, "dailyStartHour", "required");
        } else if (form.daily_start_hour < 0 || form.daily_start_hour > 23) {
          errors.daily_start_hour = resolveFieldValidationMessage(context, "dailyStartHour", "invalid");
        }

        if (!Number.isInteger(form.daily_end_hour)) {
          errors.daily_end_hour = resolveFieldValidationMessage(context, "dailyEndHour", "required");
        } else if (form.daily_end_hour < 1 || form.daily_end_hour > 24) {
          errors.daily_end_hour = resolveFieldValidationMessage(context, "dailyEndHour", "invalid");
        }

        if (
          Number.isInteger(form.daily_start_hour)
          && Number.isInteger(form.daily_end_hour)
          && form.daily_end_hour <= form.daily_start_hour
        ) {
          const hoursError = resolveFieldError(context, { error: "invalid_daily_hours" }, "");
          errors.daily_start_hour = hoursError;
          errors.daily_end_hour = hoursError;
        }

        if (!Array.isArray(form.allowed_weekdays) || form.allowed_weekdays.length === 0) {
          errors.allowed_weekdays = resolveFieldError(context, { error: "invalid_weekdays" }, "");
        }

        if (!timezoneName) {
          errors.timezone = resolveFieldValidationMessage(context, "timezone", "required");
        } else if (!isValidTimeZoneName(timezoneName)) {
          errors.timezone = resolveFieldError(context, { error: "invalid_timezone" }, "");
        }

        if (
          scope === "edit"
          && Object.keys(errors).length === 0
          && checkScheduleConflict(context, form)
        ) {
          const conflictError = resolveFieldError(
            context,
            { error: "schedule_conflicts_with_votes" },
            ""
          );
          for (const field of this.backendErrorFields("schedule_conflicts_with_votes")) {
            errors[field] = conflictError;
          }
        }

        return errors;
      }
    };
  }

  function filterTimezoneSuggestionOptions(timezoneOptions, query, buildMeta, limit = 200) {
    const metaBuilder = typeof buildMeta === "function" ? buildMeta : () => "";
    const normalizedLimit = Number.isInteger(limit) && limit > 0 ? limit : 200;
    const normalizedQuery = String(query || "").trim().toLowerCase();
    const options = Array.isArray(timezoneOptions)
      ? timezoneOptions
          .map((value) => String(value || "").trim())
          .filter(Boolean)
          .map((timeZone) => {
            const meta = String(metaBuilder(timeZone) || "").trim();
            const label = meta ? `${timeZone} ${meta}` : timeZone;
            return {
              id: timeZone,
              meta,
              label
            };
          })
      : [];

    if (!normalizedQuery) {
      return options.slice(0, normalizedLimit);
    }

    return options
      .filter((item) => item.label.toLowerCase().includes(normalizedQuery))
      .slice(0, normalizedLimit);
  }

  function autoGrowScheduleForm(form, votedBounds) {
    const nextForm = form && typeof form === "object" ? { ...form } : {};
    const normalizedBounds = votedBounds && typeof votedBounds === "object" ? votedBounds : {};
    const hasVotes = Boolean(normalizedBounds.hasVotes);

    if (!hasVotes) {
      return {
        changedFields: [],
        nextForm
      };
    }

    const changedFields = [];
    const earliestDay = normalizeIsoDayKey(normalizedBounds.earliestDay);
    const latestDay = normalizeIsoDayKey(normalizedBounds.latestDay);
    const currentStartDay = normalizeIsoDayKey(nextForm.start_date);
    const currentEndDay = normalizeIsoDayKey(nextForm.end_date);

    if (earliestDay && (!currentStartDay || currentStartDay > earliestDay)) {
      nextForm.start_date = earliestDay;
      changedFields.push("start_date");
    }

    if (latestDay && (!currentEndDay || currentEndDay < latestDay)) {
      nextForm.end_date = latestDay;
      changedFields.push("end_date");
    }

    const earliestHour = normalizeHourValue(normalizedBounds.earliestHour, 0, 23);
    const minEndHour = normalizeHourValue(normalizedBounds.minEndHour, 1, 24);
    const currentStartHour = normalizeHourValue(nextForm.daily_start_hour, 0, 23);
    const currentEndHour = normalizeHourValue(nextForm.daily_end_hour, 1, 24);

    if (earliestHour !== null && (currentStartHour === null || currentStartHour > earliestHour)) {
      nextForm.daily_start_hour = earliestHour;
      changedFields.push("daily_start_hour");
    }

    if (minEndHour !== null && (currentEndHour === null || currentEndHour < minEndHour)) {
      nextForm.daily_end_hour = minEndHour;
      changedFields.push("daily_end_hour");
    }

    const currentWeekdays = normalizeWeekdayValues(nextForm.allowed_weekdays);
    const lockedWeekdays = normalizeWeekdayValues(normalizedBounds.lockedWeekdays);
    const mergedWeekdays = Array.from(new Set([...currentWeekdays, ...lockedWeekdays])).sort(
      (left, right) => left - right
    );

    if (mergedWeekdays.join(",") !== currentWeekdays.join(",")) {
      nextForm.allowed_weekdays = mergedWeekdays;
      changedFields.push("allowed_weekdays");
    }

    return {
      changedFields,
      nextForm
    };
  }

  function defaultCalendarTimezonePreference() {
    return {
      mode: "poll",
      timezone: ""
    };
  }

  function normalizeCalendarTimezoneMode(mode) {
    return mode === "poll" || mode === "browser" || mode === "custom" ? mode : "poll";
  }

  function calendarTimezonePreferenceStorageKeyForSession(session) {
    if (!session || !session.authenticated || !session.identity || !session.identity.id) {
      return "";
    }
    return `timepoll-calendar-timezone:${session.identity.id}`;
  }

  function loadCalendarTimezonePreferenceValue(rawValue, normalizeKnownTimeZone) {
    const normalizeTimeZone =
      typeof normalizeKnownTimeZone === "function"
        ? normalizeKnownTimeZone
        : (value) => String(value || "").trim();

    if (!rawValue) {
      return defaultCalendarTimezonePreference();
    }

    try {
      const parsed = JSON.parse(rawValue);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        return {
          mode: normalizeCalendarTimezoneMode(parsed.mode),
          timezone: normalizeTimeZone(parsed.timezone)
        };
      }
    } catch (_jsonError) {}

    return defaultCalendarTimezonePreference();
  }

  function serializeCalendarTimezonePreference(
    mode,
    calendarCustomTimezone,
    showBrowserTimezoneOption,
    normalizeKnownTimeZone
  ) {
    const normalizeTimeZone =
      typeof normalizeKnownTimeZone === "function"
        ? normalizeKnownTimeZone
        : (value) => String(value || "").trim();

    let normalizedMode = normalizeCalendarTimezoneMode(mode);
    if (normalizedMode === "browser" && !showBrowserTimezoneOption) {
      normalizedMode = "poll";
    }

    const normalizedTimeZone = normalizeTimeZone(calendarCustomTimezone) || "";
    if (normalizedMode === "custom" && !normalizedTimeZone) {
      return null;
    }

    return JSON.stringify({
      mode: normalizedMode,
      timezone: normalizedTimeZone
    });
  }

  window.TimePollLogic = {
    createPollFormValidator,
    buildPollUrlState,
    calendarTimezonePreferenceStorageKeyForSession,
    collectDayOptionIdsFromRows,
    collectRowOptionIdsFromCells,
    extractPollIdFromSearch,
    filterRowsForVisibleDaysAndMinYesVotes,
    filterWeekRowsByMinYesVotes,
    filterTimezoneSuggestionOptions,
    isValidTimeZoneName,
    isVoteStatusValue,
    loadCalendarTimezonePreferenceValue,
    matchesYesVoteFilter,
    nextVoteStatus,
    parseIsoDateValue,
    readOptionCount,
    autoGrowScheduleForm,
    serializeCalendarTimezonePreference,
    toggleWeekdaySelection
  };
})();
