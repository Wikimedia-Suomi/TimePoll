function registerUnitTests(harness) {
  const {
    autoGrowScheduleForm,
    buildPollUrlState,
    calendarTimezonePreferenceStorageKeyForSession,
    collectDayOptionIdsFromRows,
    collectRowOptionIdsFromCells,
    createPollFormValidator,
    createSuggestedPollIdentifier,
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
    serializeCalendarTimezonePreference,
    toggleWeekdaySelection
  } = window.TimePollLogic || {};
  const { test, assert, assertEqual, assertDeepEqual } = harness;

  test("extractPollIdFromSearch prefers id parameter", () => {
    assertEqual(extractPollIdFromSearch("?id=Poll_Name_2026"), "Poll_Name_2026");
  });

  test("extractPollIdFromSearch ignores unrelated query parameters", () => {
    assertEqual(extractPollIdFromSearch("?poll=legacy_value"), "");
  });

  test("buildPollUrlState stores id and preserves the hash fragment", () => {
    const result = buildPollUrlState("https://example.test/#section", "New_Poll");
    assertEqual(result.normalizedPollId, "New_Poll");
    assertEqual(result.nextUrl, "/?id=New_Poll#section");
  });

  test("buildPollUrlState clears the id parameter when poll id is blank", () => {
    const result = buildPollUrlState("https://example.test/?id=Old", "   ");
    assertEqual(result.nextUrl, "/");
  });

  test("isVoteStatusValue accepts only allowed vote statuses", () => {
    assertEqual(isVoteStatusValue("yes"), true);
    assertEqual(isVoteStatusValue("maybe"), true);
    assertEqual(isVoteStatusValue("later"), false);
  });

  test("nextVoteStatus toggles an already selected vote back to empty", () => {
    assertEqual(nextVoteStatus("yes", "yes"), "");
    assertEqual(nextVoteStatus("yes", "maybe"), "maybe");
  });

  test("readOptionCount handles sparse vote payloads", () => {
    assertEqual(readOptionCount({ counts: { yes: "2" } }, "yes"), 2);
    assertEqual(readOptionCount({ counts: {} }, "maybe"), 0);
  });

  test("matchesYesVoteFilter checks the yes counter threshold", () => {
    assertEqual(matchesYesVoteFilter({ counts: { yes: 3 } }, 2), true);
    assertEqual(matchesYesVoteFilter({ counts: { yes: 1 } }, 2), false);
  });

  test("filterWeekRowsByMinYesVotes keeps only visible yes-threshold cells", () => {
    const week = {
      rows: [
        {
          key: "09:00",
          cells: {
            "2026-04-01": { id: 1, counts: { yes: 2 } },
            "2026-04-02": { id: 2, counts: { yes: 0 } }
          }
        },
        {
          key: "10:00",
          cells: {
            "2026-04-01": { id: 3, counts: { yes: 1 } }
          }
        }
      ]
    };

    assertDeepEqual(filterWeekRowsByMinYesVotes(week, 2), [
      {
        key: "09:00",
        cells: {
          "2026-04-01": { id: 1, counts: { yes: 2 } }
        }
      }
    ]);
  });

  test("filterRowsForVisibleDaysAndMinYesVotes removes rows that only match outside the visible block", () => {
    const rows = [
      {
        key: "09:00",
        cells: {
          "2026-04-13": { id: 1, counts: { yes: 2 } },
          "2026-04-14": { id: 2, counts: { yes: 0 } },
          "2026-04-17": { id: 3, counts: { yes: 0 } }
        }
      }
    ];

    assertDeepEqual(
      filterRowsForVisibleDaysAndMinYesVotes(rows, ["2026-04-17"], 2),
      []
    );
    assertDeepEqual(
      filterRowsForVisibleDaysAndMinYesVotes(rows, ["2026-04-13", "2026-04-14"], 2),
      [
        {
          key: "09:00",
          cells: {
            "2026-04-13": { id: 1, counts: { yes: 2 } }
          }
        }
      ]
    );
  });

  test("filterTimezoneSuggestionOptions filters using timezone id and meta text", () => {
    const results = filterTimezoneSuggestionOptions(
      ["UTC", "Europe/Helsinki", "Europe/Stockholm"],
      "helsinki utc+3",
      (timeZone) => (timeZone === "Europe/Helsinki" ? "UTC+3" : "")
    );

    assertDeepEqual(results, [
      {
        id: "Europe/Helsinki",
        meta: "UTC+3",
        label: "Europe/Helsinki UTC+3"
      }
    ]);
  });

  test("parseIsoDateValue rejects invalid dates and accepts canonical YYYY-MM-DD values", () => {
    assertEqual(parseIsoDateValue("2026-04-31"), null);
    assertEqual(parseIsoDateValue("2026-04-30") instanceof Date, true);
  });

  test("isValidTimeZoneName accepts known IANA zones", () => {
    assertEqual(isValidTimeZoneName("Europe/Helsinki"), true);
    assertEqual(isValidTimeZoneName("Europe/Not-A-Timezone"), false);
  });

  test("collectDayOptionIdsFromRows returns ids for one visible day", () => {
    const rows = [
      { cells: { "2026-04-01": { id: 11 }, "2026-04-02": { id: 12 } } },
      { cells: { "2026-04-01": { id: 21 } } },
      { cells: { "2026-04-02": { id: 22 } } }
    ];
    assertDeepEqual(collectDayOptionIdsFromRows(rows, "2026-04-01"), [11, 21]);
  });

  test("collectRowOptionIdsFromCells supports full row and limited visible day keys", () => {
    const row = {
      cells: {
        "2026-04-01": { id: 1 },
        "2026-04-02": { id: 2 },
        "2026-04-03": { id: 3 }
      }
    };

    assertDeepEqual(collectRowOptionIdsFromCells(row, ["2026-04-01", "2026-04-03"]), [1, 3]);
    assertDeepEqual(collectRowOptionIdsFromCells(row), [1, 2, 3]);
  });

  test("toggleWeekdaySelection sorts and de-duplicates weekday values", () => {
    assertDeepEqual(toggleWeekdaySelection([4, 2, 2], 1), [1, 2, 4]);
    assertDeepEqual(toggleWeekdaySelection([1, 2, 4], 2), [1, 4]);
  });

  test("createPollFormValidator centralizes create form rules and backend field mapping", () => {
    const validator = createPollFormValidator({
      fieldValidationMessage: (_context, fieldKey, kind) => `${fieldKey}:${kind}`,
      resolveError: (_context, payload, fallback) => payload.error || fallback || "",
      hasScheduleConflictWithVotes: () => false
    });

    assertDeepEqual(
      validator.buildErrors(
        {},
        {
          title: "",
          identifier: "bad slug",
          start_date: "2026-05-10",
          end_date: "2026-05-09",
          daily_start_hour: 12,
          daily_end_hour: 12,
          allowed_weekdays: [],
          timezone: "Europe/Not-A-Timezone"
        },
        { scope: "create" }
      ),
      {
        title: "title:required",
        identifier: "invalid_poll_identifier",
        start_date: "invalid_date_range",
        end_date: "invalid_date_range",
        daily_start_hour: "invalid_daily_hours",
        daily_end_hour: "invalid_daily_hours",
        allowed_weekdays: "invalid_weekdays",
        timezone: "invalid_timezone"
      }
    );

    assertDeepEqual(
      validator.backendErrorFields("too_many_options"),
      ["start_date", "end_date", "daily_start_hour", "daily_end_hour", "allowed_weekdays"]
    );
  });

  test("createSuggestedPollIdentifier generates five uppercase alphanumeric characters", () => {
    const identifier = createSuggestedPollIdentifier((index) => [0, 0.25, 0.5, 0.75, 0.999][index]);
    assertEqual(identifier.length, 5);
    assertEqual(/^[A-Z0-9]{5}$/.test(identifier), true);
  });

  test("autoGrowScheduleForm expands days, hours and weekdays to keep votes in range", () => {
    const result = autoGrowScheduleForm(
      {
        start_date: "2026-05-04",
        end_date: "2026-05-04",
        daily_start_hour: 9,
        daily_end_hour: 17,
        allowed_weekdays: [0]
      },
      {
        earliestDay: "2026-05-03",
        latestDay: "2026-05-05",
        earliestHour: 8,
        minEndHour: 19,
        lockedWeekdays: [6, 0, 2],
        hasVotes: true
      }
    );

    assertDeepEqual(result.nextForm, {
      start_date: "2026-05-03",
      end_date: "2026-05-05",
      daily_start_hour: 8,
      daily_end_hour: 19,
      allowed_weekdays: [0, 2, 6]
    });
    assertDeepEqual(result.changedFields, [
      "start_date",
      "end_date",
      "daily_start_hour",
      "daily_end_hour",
      "allowed_weekdays"
    ]);
  });

  test("autoGrowScheduleForm never shrinks an already wide enough schedule", () => {
    const result = autoGrowScheduleForm(
      {
        start_date: "2026-05-01",
        end_date: "2026-05-08",
        daily_start_hour: 6,
        daily_end_hour: 22,
        allowed_weekdays: [0, 1, 2, 3, 4, 5, 6]
      },
      {
        earliestDay: "2026-05-03",
        latestDay: "2026-05-05",
        earliestHour: 8,
        minEndHour: 19,
        lockedWeekdays: [0, 2],
        hasVotes: true
      }
    );

    assertDeepEqual(result.nextForm, {
      start_date: "2026-05-01",
      end_date: "2026-05-08",
      daily_start_hour: 6,
      daily_end_hour: 22,
      allowed_weekdays: [0, 1, 2, 3, 4, 5, 6]
    });
    assertDeepEqual(result.changedFields, []);
  });

  test("calendarTimezonePreferenceStorageKeyForSession uses authenticated identity id", () => {
    assertEqual(
      calendarTimezonePreferenceStorageKeyForSession({
        authenticated: true,
        identity: { id: 42 }
      }),
      "timepoll-calendar-timezone:42"
    );
    assertEqual(calendarTimezonePreferenceStorageKeyForSession({ authenticated: false }), "");
  });

  test("loadCalendarTimezonePreferenceValue reads structured JSON values", () => {
    const result = loadCalendarTimezonePreferenceValue(
      JSON.stringify({ mode: "custom", timezone: "europe/helsinki" }),
      (value) => (String(value).toLowerCase() === "europe/helsinki" ? "Europe/Helsinki" : "")
    );

    assertDeepEqual(result, {
      mode: "custom",
      timezone: "Europe/Helsinki"
    });
  });

  test("loadCalendarTimezonePreferenceValue resets invalid data to defaults", () => {
    const result = loadCalendarTimezonePreferenceValue("UTC", (value) => String(value || "").trim());
    assertDeepEqual(result, {
      mode: "poll",
      timezone: ""
    });
  });

  test("serializeCalendarTimezonePreference normalizes browser and custom modes", () => {
    assertEqual(
      serializeCalendarTimezonePreference("browser", "UTC", false, (value) => String(value || "").trim()),
      JSON.stringify({ mode: "poll", timezone: "UTC" })
    );

    assertEqual(
      serializeCalendarTimezonePreference("custom", "  ", true, () => ""),
      null
    );
  });

  test("unit harness assert helper remains available", () => {
    assert(true, "Expected truthy assertion.");
  });
}

window.registerTimePollLogicUnitTests = registerUnitTests;
