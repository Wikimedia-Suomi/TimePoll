function registerUnitTests(harness) {
  const {
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
