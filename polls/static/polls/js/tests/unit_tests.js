function registerUnitTests(harness) {
  const {
    autoGrowScheduleForm,
    buildPollUrlState,
    calendarTimezonePreferenceStorageKeyForSession,
    collectDayOptionIdsFromRows,
    collectRowOptionIdsFromCells,
    extractPollIdFromSearch,
    filterRowsForVisibleDaysAndMinYesVotes,
    filterWeekRowsByMinYesVotes,
    isVoteStatusValue,
    loadCalendarTimezonePreferenceValue,
    matchesYesVoteFilter,
    nextVoteStatus,
    optionHasVotes,
    readOptionCount,
    serializeCalendarTimezonePreference,
    toggleWeekdaySelection
  } = window.TimePollLogic || {};
  const { test, assert, assertEqual, assertDeepEqual } = harness;

  test("extractPollIdFromSearch prefers id parameter", () => {
    assertEqual(extractPollIdFromSearch("?poll=legacy&id=Poll_Name_2026"), "Poll_Name_2026");
  });

  test("extractPollIdFromSearch falls back to legacy poll parameter", () => {
    assertEqual(extractPollIdFromSearch("?poll=legacy_value"), "legacy_value");
  });

  test("buildPollUrlState stores id and removes legacy poll parameter", () => {
    const result = buildPollUrlState("https://example.test/?poll=old#section", "New_Poll");
    assertEqual(result.normalizedPollId, "New_Poll");
    assertEqual(result.nextUrl, "/?id=New_Poll#section");
  });

  test("buildPollUrlState clears id and poll parameters when poll id is blank", () => {
    const result = buildPollUrlState("https://example.test/?id=Old&poll=legacy", "   ");
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

  test("readOptionCount and optionHasVotes handle sparse vote payloads", () => {
    assertEqual(readOptionCount({ counts: { yes: "2" } }, "yes"), 2);
    assertEqual(readOptionCount({ counts: {} }, "maybe"), 0);
    assertEqual(optionHasVotes({ counts: { no: 1 } }), true);
    assertEqual(optionHasVotes({ counts: { yes: 0, no: 0, maybe: 0 } }), false);
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

  test("loadCalendarTimezonePreferenceValue supports legacy raw timezone values", () => {
    const result = loadCalendarTimezonePreferenceValue("UTC", (value) => String(value || "").trim());
    assertDeepEqual(result, {
      mode: "custom",
      timezone: "UTC"
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
