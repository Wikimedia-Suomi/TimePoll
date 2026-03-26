(() => {
  function extractPollIdFromSearch(search) {
    try {
      const params = new URLSearchParams(String(search || ""));
      const primaryValue = String(params.get("id") || "").trim();
      if (primaryValue) {
        return primaryValue;
      }
      return String(params.get("poll") || "").trim();
    } catch (_error) {
      return "";
    }
  }

  function buildPollUrlState(currentHref, pollId) {
    const normalizedPollId = String(pollId || "").trim();
    const url = new URL(String(currentHref || "/"), "https://timepoll.local");

    if (normalizedPollId) {
      url.searchParams.set("id", normalizedPollId);
      url.searchParams.delete("poll");
    } else {
      url.searchParams.delete("id");
      url.searchParams.delete("poll");
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

  function optionHasVotes(option) {
    if (!option || typeof option !== "object") {
      return false;
    }
    if (Array.isArray(option.votes)) {
      return option.votes.length > 0;
    }
    return (
      readOptionCount(option, "yes")
      + readOptionCount(option, "no")
      + readOptionCount(option, "maybe")
      > 0
    );
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

    const normalizedMinYesVotes = Math.max(0, Number(minYesVotes) || 0);
    if (normalizedMinYesVotes <= 0) {
      return week.rows;
    }

    const filteredRows = [];
    for (const row of week.rows) {
      if (!row || !row.cells || typeof row.cells !== "object") {
        continue;
      }
      const filteredCells = {};
      for (const [dayKey, option] of Object.entries(row.cells)) {
        if (matchesYesVoteFilter(option, normalizedMinYesVotes)) {
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
    } catch (_jsonError) {
      // Support legacy raw timezone values.
    }

    const legacyTimeZone = normalizeTimeZone(rawValue);
    if (legacyTimeZone) {
      return {
        mode: "custom",
        timezone: legacyTimeZone
      };
    }

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
    buildPollUrlState,
    calendarTimezonePreferenceStorageKeyForSession,
    collectDayOptionIdsFromRows,
    collectRowOptionIdsFromCells,
    extractPollIdFromSearch,
    filterWeekRowsByMinYesVotes,
    isVoteStatusValue,
    loadCalendarTimezonePreferenceValue,
    matchesYesVoteFilter,
    nextVoteStatus,
    optionHasVotes,
    readOptionCount,
    autoGrowScheduleForm,
    serializeCalendarTimezonePreference,
    toggleWeekdaySelection
  };
})();
