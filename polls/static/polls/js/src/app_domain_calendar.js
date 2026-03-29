(() => {
  const domains = window.TimePollAppDomains || (window.TimePollAppDomains = {});

  domains.createCalendarDomainMethods = function createCalendarDomainMethods({
    calendarTimezonePreferenceStorageKeyForSession,
    cappedDayColumnWidthPx,
    collectDayOptionIdsFromRows,
    collectRowOptionIdsFromCells,
    estimateTimeColumnWidthPx,
    filterRowsForVisibleDaysAndMinYesVotes,
    filterWeekRowsByMinYesVotes,
    isVoteStatusValue,
    loadCalendarTimezonePreferenceValue,
    matchesYesVoteFilter,
    nextVoteStatus,
    readOptionCount,
    safeLocalStorageGetItem,
    safeLocalStorageSetItem,
    serializeCalendarTimezonePreference,
    visibleDayCountForWidth,
    voteSyncDebounceMs,
    apiFetch,
    languageMap
  }) {
    return {
      bulkMenuStatuses() {
        return ["", "yes", "maybe", "no"];
      },
      bulkMenuIdPart(value) {
        return String(value || "").replace(/[^A-Za-z0-9_-]+/g, "-");
      },
      bulkMenuTriggerId(type, scopeKey, key) {
        return `bulk-trigger-${this.bulkMenuIdPart(type)}-${this.bulkMenuIdPart(scopeKey)}-${this.bulkMenuIdPart(key)}`;
      },
      bulkMenuId(type, scopeKey, key) {
        return `bulk-menu-${this.bulkMenuIdPart(type)}-${this.bulkMenuIdPart(scopeKey)}-${this.bulkMenuIdPart(key)}`;
      },
      bulkMenuItemId(type, scopeKey, key, status) {
        const suffix = status || "none";
        return `bulk-menu-item-${this.bulkMenuIdPart(type)}-${this.bulkMenuIdPart(scopeKey)}-${this.bulkMenuIdPart(key)}-${this.bulkMenuIdPart(suffix)}`;
      },
      focusBulkTrigger(type, scopeKey, key) {
        const trigger = document.getElementById(this.bulkMenuTriggerId(type, scopeKey, key));
        if (trigger && typeof trigger.focus === "function") {
          trigger.focus();
        }
      },
      focusBulkMenuItem(type, scopeKey, key, status = "") {
        const menuItem = document.getElementById(this.bulkMenuItemId(type, scopeKey, key, status));
        if (menuItem && typeof menuItem.focus === "function") {
          menuItem.focus();
        }
      },
      voteCellMenuScopeKey() {
        return "option";
      },
      voteCellTriggerId(optionOrId) {
        const optionId = typeof optionOrId === "object"
          ? Number(optionOrId && optionOrId.id)
          : Number(optionOrId);
        if (!Number.isInteger(optionId)) {
          return "";
        }
        return this.bulkMenuTriggerId("cell", this.voteCellMenuScopeKey(), optionId);
      },
      voteCellMenuId(optionOrId) {
        const optionId = typeof optionOrId === "object"
          ? Number(optionOrId && optionOrId.id)
          : Number(optionOrId);
        if (!Number.isInteger(optionId)) {
          return "";
        }
        return this.bulkMenuId("cell", this.voteCellMenuScopeKey(), optionId);
      },
      voteCellMenuItemId(optionOrId, status) {
        const optionId = typeof optionOrId === "object"
          ? Number(optionOrId && optionOrId.id)
          : Number(optionOrId);
        if (!Number.isInteger(optionId)) {
          return "";
        }
        return this.bulkMenuItemId("cell", this.voteCellMenuScopeKey(), optionId, status);
      },
      isVoteCellMenuOpen(optionOrId) {
        const optionId = typeof optionOrId === "object"
          ? Number(optionOrId && optionOrId.id)
          : Number(optionOrId);
        if (!Number.isInteger(optionId)) {
          return false;
        }
        return this.isBulkMenuOpen("cell", this.voteCellMenuScopeKey(), optionId);
      },
      timezoneDateParts(value, timeZone) {
        if (!value) {
          return null;
        }
        const parsed = new Date(value);
        if (Number.isNaN(parsed.getTime())) {
          return null;
        }
        const parts = new Intl.DateTimeFormat("en-CA", {
          timeZone: timeZone || "UTC",
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
          hourCycle: "h23"
        }).formatToParts(parsed);

        const values = {};
        for (const part of parts) {
          if (part.type !== "literal") {
            values[part.type] = part.value;
          }
        }

        if (!values.year || !values.month || !values.day || values.hour === undefined || values.minute === undefined) {
          return null;
        }

        return {
          dayKey: `${values.year}-${values.month}-${values.day}`,
          timeKey: `${values.hour}:${values.minute}`
        };
      },
      dayKeyToUtcDate(dayKey) {
        if (typeof dayKey !== "string") {
          return null;
        }
        const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dayKey);
        if (!match) {
          return null;
        }

        const year = Number(match[1]);
        const month = Number(match[2]);
        const day = Number(match[3]);

        if (!Number.isInteger(year) || !Number.isInteger(month) || !Number.isInteger(day)) {
          return null;
        }
        if (month < 1 || month > 12 || day < 1 || day > 31) {
          return null;
        }

        return new Date(Date.UTC(year, month - 1, day));
      },
      dayGapCountBetween(previousDayKey, nextDayKey) {
        const previousDate = this.dayKeyToUtcDate(previousDayKey);
        const nextDate = this.dayKeyToUtcDate(nextDayKey);
        if (!previousDate || !nextDate) {
          return 0;
        }
        const diffMs = nextDate.getTime() - previousDate.getTime();
        const diffDays = Math.round(diffMs / 86400000);
        return diffDays > 1 ? diffDays - 1 : 0;
      },
      dayHasGapBefore(days, dayIndex) {
        if (!Array.isArray(days) || dayIndex <= 0 || dayIndex >= days.length) {
          return false;
        }
        const previousDay = days[dayIndex - 1];
        const currentDay = days[dayIndex];
        return this.dayGapCountBetween(previousDay && previousDay.key, currentDay && currentDay.key) > 0;
      },
      weekStartKey(dayKey) {
        const utcDate = this.dayKeyToUtcDate(dayKey);
        if (!utcDate) {
          return dayKey;
        }
        const weekday = utcDate.getUTCDay();
        const diffToMonday = weekday === 0 ? -6 : 1 - weekday;
        utcDate.setUTCDate(utcDate.getUTCDate() + diffToMonday);
        return utcDate.toISOString().slice(0, 10);
      },
      formatDayLabel(dayKey) {
        const utcDate = this.dayKeyToUtcDate(dayKey);
        if (!utcDate) {
          return dayKey;
        }
        return new Intl.DateTimeFormat(languageMap[this.language] || "en-GB", {
          weekday: "short",
          day: "2-digit",
          month: "2-digit",
          timeZone: "UTC"
        }).format(utcDate);
      },
      formatDayLongLabel(dayKey) {
        const utcDate = this.dayKeyToUtcDate(dayKey);
        if (!utcDate) {
          return dayKey;
        }
        return new Intl.DateTimeFormat(languageMap[this.language] || "en-GB", {
          weekday: "long",
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
          timeZone: "UTC"
        }).format(utcDate);
      },
      formatWeekTitle(weekKey) {
        const utcDate = this.dayKeyToUtcDate(weekKey);
        if (!utcDate) {
          return `${this.t("weekOf")} ${weekKey}`;
        }
        const formatted = new Intl.DateTimeFormat(languageMap[this.language] || "en-GB", {
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
          timeZone: "UTC"
        }).format(utcDate);
        return `${this.t("weekOf")} ${formatted}`;
      },
      normalizeVoteValue(value, fallback = "") {
        if (value === "yes" || value === "no" || value === "maybe") {
          return value;
        }
        if (value === "" || value === null) {
          return "";
        }
        if (fallback === "yes" || fallback === "no" || fallback === "maybe") {
          return fallback;
        }
        return "";
      },
      confirmedVoteValueForOption(option) {
        if (!option || typeof option !== "object") {
          return "";
        }
        return this.normalizeVoteValue(option.my_vote);
      },
      voteValueForOption(option) {
        if (!option) {
          return "";
        }
        const confirmedValue = this.confirmedVoteValueForOption(option);
        if (!Object.prototype.hasOwnProperty.call(this.voteDraft, option.id)) {
          return confirmedValue;
        }
        return this.normalizeVoteValue(this.voteDraft[option.id], confirmedValue);
      },
      displayedVoteValueForOption(option) {
        if (!option || !Number.isInteger(option.id)) {
          return "";
        }
        if (
          this.bulkMenu
          && this.bulkMenu.type === "cell"
          && this.bulkMenu.scopeKey === this.voteCellMenuScopeKey()
          && Number(this.bulkMenu.key) === option.id
          && this.voteCellMenuPreview
          && Number(this.voteCellMenuPreview.optionId) === option.id
        ) {
          return this.isVoteStatus(this.voteCellMenuPreview.status) ? this.voteCellMenuPreview.status : "";
        }
        return this.voteValueForOption(option);
      },
      voteCellClass(option) {
        if (!option || typeof option !== "object") {
          return "vote-none";
        }
        if (this.voteDisplayMode === "own") {
          const ownValue = this.displayedVoteValueForOption(option);
          if (ownValue === "yes") {
            return "vote-yes";
          }
          if (ownValue === "no") {
            return "vote-no";
          }
          if (ownValue === "maybe") {
            return "vote-maybe";
          }
          return "vote-none";
        }
        const yesCount = this.optionCount(option, "yes");
        const noCount = this.optionCount(option, "no");

        if (yesCount > noCount) {
          return "vote-yes";
        }
        if (yesCount < noCount) {
          return "vote-no";
        }
        return "vote-none";
      },
      isDisplayedVoteValue(option, status) {
        return this.displayedVoteValueForOption(option) === status;
      },
      optionCount(option, status) {
        const baseCount = readOptionCount(option, status);
        if (!option || !this.isVoteStatus(status)) {
          return baseCount;
        }
        const confirmedValue = this.confirmedVoteValueForOption(option);
        const desiredValue = this.voteValueForOption(option);
        let adjustedCount = baseCount;
        if (confirmedValue !== desiredValue) {
          if (confirmedValue === status && adjustedCount > 0) {
            adjustedCount -= 1;
          }
          if (desiredValue === status) {
            adjustedCount += 1;
          }
        }
        return adjustedCount;
      },
      voteStatusLabel(status) {
        if (status === "yes") {
          return this.t("voteYes");
        }
        if (status === "no") {
          return this.t("voteNo");
        }
        if (status === "maybe") {
          return this.t("voteMaybe");
        }
        return this.t("noVote");
      },
      isVoteStatus(status) {
        return isVoteStatusValue(status);
      },
      closeVoteMenus(options = {}) {
        const activeMenu = this.bulkMenu;
        this.bulkMenu = null;
        this.voteCellMenuPreview = null;
        if (options.restoreFocus && activeMenu) {
          this.$nextTick(() => {
            this.focusBulkTrigger(activeMenu.type, activeMenu.scopeKey, activeMenu.key);
          });
        }
      },
      updateVisibleDayCount() {
        const root = document.getElementById("app");
        if (!root) {
          return;
        }
        const tableWrap = root.querySelector(".details .table-wrap");
        const wrapWidth = tableWrap ? tableWrap.clientWidth : root.clientWidth || window.innerWidth;
        this.calendarWrapWidth = wrapWidth;
        const nextCount = visibleDayCountForWidth(wrapWidth);
        if (nextCount !== this.visibleDayCount) {
          this.visibleDayCount = nextCount;
        }
      },
      visibleRenderedDayCountForBlock(block) {
        return Array.isArray(block && block.days) && block.days.length ? block.days.length : 1;
      },
      calendarDayColumnWidthPxForBlock(block) {
        const referenceDayCount = this.visibleRenderedDayCountForBlock(block);
        const fallbackWidth = typeof window !== "undefined" ? window.innerWidth : 0;
        const wrapWidth = this.calendarWrapWidth || fallbackWidth;
        return cappedDayColumnWidthPx(wrapWidth, referenceDayCount);
      },
      calendarDayColumnStyleForBlock(block) {
        const widthPx = this.calendarDayColumnWidthPxForBlock(block);
        return {
          width: `${widthPx}px`,
          maxWidth: "18em"
        };
      },
      calendarTableStyleForBlock(block) {
        const dayCount = this.visibleRenderedDayCountForBlock(block);
        const viewportWidth = typeof window !== "undefined" ? window.innerWidth : this.calendarWrapWidth;
        const timeWidth = estimateTimeColumnWidthPx(viewportWidth || 0);
        const dayWidth = this.calendarDayColumnWidthPxForBlock(block);
        return {
          width: `${timeWidth + (dayWidth * dayCount)}px`
        };
      },
      visibleDayCountForWeek(week) {
        if (!week || !Array.isArray(week.days) || week.days.length === 0) {
          return 1;
        }
        return Math.max(1, Math.min(this.visibleDayCount, week.days.length));
      },
      weekBlocksForWeek(week) {
        if (!week || !Array.isArray(week.days) || week.days.length === 0) {
          return [];
        }
        const count = this.visibleDayCountForWeek(week);
        const totalDays = week.days.length;
        const blockCount = Math.max(1, Math.ceil(totalDays / count));
        const baseSize = Math.floor(totalDays / blockCount);
        let remainder = totalDays % blockCount;
        const blocks = [];
        let startIndex = 0;
        for (let blockIndex = 0; blockIndex < blockCount; blockIndex += 1) {
          const blockSize = baseSize + (remainder > 0 ? 1 : 0);
          if (remainder > 0) {
            remainder -= 1;
          }
          const days = week.days.slice(startIndex, startIndex + blockSize);
          blocks.push({
            key: `${week.key}-block-${blockIndex}`,
            index: blockIndex,
            startIndex,
            days
          });
          startIndex += blockSize;
        }
        return blocks;
      },
      weekBlockCount(week) {
        return this.weekBlocksForWeek(week).length;
      },
      hasMultipleWeekBlocks(week) {
        return this.weekBlockCount(week) > 1;
      },
      calendarBlockEntries() {
        const entries = [];
        for (const week of this.calendarWeeks) {
          const blocks = this.weekBlocksForWeek(week);
          for (const block of blocks) {
            entries.push({
              week,
              weekKey: week.key,
              block,
              blockKey: block.key
            });
          }
        }
        return entries;
      },
      findCalendarBlockEntryIndex(week, block, entries = null) {
        if (!week || !block) {
          return -1;
        }
        const sourceEntries = Array.isArray(entries) ? entries : this.calendarBlockEntries();
        return sourceEntries.findIndex(
          (entry) => entry.weekKey === week.key && entry.blockKey === block.key
        );
      },
      adjacentCalendarBlockEntry(week, block, direction) {
        const entries = this.calendarBlockEntries();
        const currentIndex = this.findCalendarBlockEntryIndex(week, block, entries);
        if (currentIndex < 0) {
          return null;
        }
        const targetIndex = currentIndex + (direction < 0 ? -1 : 1);
        return entries[targetIndex] || null;
      },
      hasWeekBlockNavigation(week, block) {
        return Boolean(
          this.adjacentCalendarBlockEntry(week, block, -1)
          || this.adjacentCalendarBlockEntry(week, block, 1)
        );
      },
      optionMatchesYesFilter(option, minYesVotes) {
        return matchesYesVoteFilter(option, minYesVotes);
      },
      filteredRowsForWeek(week) {
        return filterWeekRowsByMinYesVotes(week, this.minYesVotesFilter);
      },
      filteredRowsForBlock(week, block) {
        const rows = Array.isArray(week && week.rows) ? week.rows : [];
        const visibleDayKeys = Array.isArray(block && block.days)
          ? block.days.map((day) => day && day.key).filter((dayKey) => Boolean(dayKey))
          : [];
        return filterRowsForVisibleDaysAndMinYesVotes(rows, visibleDayKeys, this.minYesVotesFilter);
      },
      weekBlockRangeLabel(week, block) {
        if (!week || !Array.isArray(week.days) || week.days.length === 0 || !block || !Array.isArray(block.days)) {
          return "";
        }
        const start = block.startIndex + 1;
        const end = Math.min(week.days.length, block.startIndex + block.days.length);
        return `${this.t("daysRange")} ${start}-${end}/${week.days.length}`;
      },
      weekBlockRangeId(week, block) {
        if (!week || !block) {
          return "";
        }
        return `calendar-week-block-range-${this.bulkMenuIdPart(week.key)}-${this.bulkMenuIdPart(block.key)}`;
      },
      weekBlockNavigationLabel(week, block, direction) {
        const base = direction < 0 ? this.t("prevDays") : this.t("nextDays");
        const range = this.weekBlockRangeLabel(week, block);
        return range ? `${base}, ${range}` : base;
      },
      weekBlockId(week, block) {
        if (!week || !block) {
          return "";
        }
        return `calendar-week-block-${this.bulkMenuIdPart(week.key)}-${this.bulkMenuIdPart(block.key)}`;
      },
      canScrollWeekBlock(week, block, direction) {
        return Boolean(this.adjacentCalendarBlockEntry(week, block, direction));
      },
      scrollToWeekBlock(week, block, direction = 0) {
        if (!week || !block) {
          return;
        }
        this.closeVoteMenus();
        const targetId = this.weekBlockId(week, block);
        this.$nextTick(() => {
          const targetElement = document.getElementById(targetId);
          if (!targetElement) {
            return;
          }
          const focusTarget = () => {
            const preferredSelector = direction < 0
              ? '[data-nav-direction="prev"]'
              : '[data-nav-direction="next"]';
            const fallbackSelector = direction < 0
              ? '[data-nav-direction="next"]'
              : '[data-nav-direction="prev"]';
            const preferredButton = direction
              ? targetElement.querySelector(preferredSelector)
              : null;
            const fallbackButton = direction
              ? targetElement.querySelector(fallbackSelector)
              : null;
            const focusCandidate = [preferredButton, fallbackButton, targetElement]
              .find((element) => element && !element.disabled && typeof element.focus === "function");
            if (focusCandidate) {
              focusCandidate.focus();
            }
          };
          const scrollTop = typeof window !== "undefined" ? window.scrollY || window.pageYOffset || 0 : 0;
          const targetTop = scrollTop + targetElement.getBoundingClientRect().top - 16;
          if (typeof window !== "undefined" && typeof window.scrollTo === "function") {
            window.scrollTo({
              top: Math.max(0, targetTop),
              behavior: "auto"
            });
            if (typeof window.requestAnimationFrame === "function") {
              window.requestAnimationFrame(() => {
                focusTarget();
              });
            } else {
              focusTarget();
            }
          } else if (typeof targetElement.scrollIntoView === "function") {
            targetElement.scrollIntoView({ block: "start", inline: "nearest" });
            focusTarget();
          }
        });
      },
      jumpWeekBlocks(week, block, direction) {
        const targetEntry = this.adjacentCalendarBlockEntry(week, block, direction);
        if (!targetEntry) {
          return;
        }
        this.scrollToWeekBlock(targetEntry.week, targetEntry.block, direction);
      },
      rowAccessibleTimeLabel(row) {
        if (!row) {
          return "";
        }
        const timeKey = typeof row.timeKey === "string" ? row.timeKey : "";
        const occurrenceCount = Number(row.occurrenceCount) || 0;
        const occurrenceIndex = Number(row.occurrenceIndex) || 0;
        if (occurrenceCount > 1) {
          return `${timeKey} [${occurrenceIndex + 1}/${occurrenceCount}]`;
        }
        return timeKey;
      },
      voteGroupAccessibleLabel(day, row) {
        const parts = [];
        if (day && typeof day.longLabel === "string" && day.longLabel) {
          parts.push(day.longLabel);
        }
        const timeLabel = this.rowAccessibleTimeLabel(row);
        if (timeLabel) {
          parts.push(timeLabel);
        }
        return parts.join(" ");
      },
      blockRowMenuKey(block, row) {
        if (!block || !row) {
          return "";
        }
        return `${block.key}-${row.timeKey}-${Number(row.occurrenceIndex) || 0}`;
      },
      isBulkMenuOpen(type, scopeKey, key) {
        return Boolean(
          this.bulkMenu &&
          this.bulkMenu.type === type &&
          this.bulkMenu.scopeKey === scopeKey &&
          this.bulkMenu.key === key
        );
      },
      toggleBulkMenu(type, scopeKey, key) {
        if (!this.canVoteInPoll) {
          return;
        }
        const isOpen = this.isBulkMenuOpen(type, scopeKey, key);
        this.bulkMenu = isOpen ? null : { type, scopeKey, key };
      },
      openBulkMenu(type, scopeKey, key, options = {}) {
        if (!this.canVoteInPoll) {
          return;
        }
        this.bulkMenu = { type, scopeKey, key };
        if (Object.prototype.hasOwnProperty.call(options, "focusStatus")) {
          this.$nextTick(() => {
            this.focusBulkMenuItem(type, scopeKey, key, options.focusStatus);
          });
        }
      },
      handleBulkTriggerKeydown(event, type, scopeKey, key) {
        if (!this.canVoteInPoll) {
          return;
        }
        if (event.key === "ArrowDown" || event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          this.openBulkMenu(type, scopeKey, key, { focusStatus: "" });
          return;
        }
        if (event.key === "ArrowUp") {
          event.preventDefault();
          this.openBulkMenu(type, scopeKey, key, { focusStatus: "maybe" });
          return;
        }
        if (event.key === "Escape" && this.isBulkMenuOpen(type, scopeKey, key)) {
          event.preventDefault();
          this.closeVoteMenus({ restoreFocus: true });
        }
      },
      handleBulkMenuKeydown(event, type, scopeKey, key) {
        const items = this.bulkMenuStatuses()
          .map((status) => document.getElementById(this.bulkMenuItemId(type, scopeKey, key, status)))
          .filter((item) => item && !item.disabled);
        if (!items.length) {
          return;
        }
        const currentIndex = items.findIndex((item) => item === document.activeElement);
        if (event.key === "ArrowDown" || event.key === "ArrowRight") {
          event.preventDefault();
          const nextIndex = currentIndex >= 0 ? (currentIndex + 1) % items.length : 0;
          items[nextIndex].focus();
          return;
        }
        if (event.key === "ArrowUp" || event.key === "ArrowLeft") {
          event.preventDefault();
          const nextIndex = currentIndex >= 0 ? (currentIndex - 1 + items.length) % items.length : items.length - 1;
          items[nextIndex].focus();
          return;
        }
        if (event.key === "Home") {
          event.preventDefault();
          items[0].focus();
          return;
        }
        if (event.key === "End") {
          event.preventDefault();
          items[items.length - 1].focus();
          return;
        }
        if (event.key === "Escape") {
          event.preventDefault();
          this.closeVoteMenus({ restoreFocus: true });
          return;
        }
        if (event.key === "Tab") {
          this.closeVoteMenus();
        }
      },
      collectDayOptionIds(week, dayKey) {
        return collectDayOptionIdsFromRows(this.filteredRowsForWeek(week), dayKey);
      },
      collectRowOptionIds(row, dayKeys) {
        return collectRowOptionIdsFromCells(row, dayKeys);
      },
      async chooseBulkVoteForDay(week, dayKey, status) {
        this.closeVoteMenus({ restoreFocus: true });
        await this.applyVotes(this.collectDayOptionIds(week, dayKey), status);
      },
      async chooseBulkVoteForRow(block, row, status) {
        this.closeVoteMenus({ restoreFocus: true });
        const visibleDayKeys = Array.isArray(block && block.days) ? block.days.map((day) => day.key) : [];
        await this.applyVotes(this.collectRowOptionIds(row, visibleDayKeys), status);
      },
      voteCellCountsAccessibleLabel(option) {
        if (!option) {
          return "";
        }
        return [
          `${this.t("yesVotes")}: ${this.optionCount(option, "yes")}`,
          `${this.t("maybeVotes")}: ${this.optionCount(option, "maybe")}`,
          `${this.t("noVotes")}: ${this.optionCount(option, "no")}`
        ].join(". ");
      },
      voteCellAccessibleLabel(day, row, option) {
        const parts = [];
        const groupLabel = this.voteGroupAccessibleLabel(day, row);
        if (groupLabel) {
          parts.push(groupLabel);
        }
        if (option) {
          parts.push(`${this.t("myVote")}: ${this.voteStatusLabel(this.voteValueForOption(option))}`);
          parts.push(this.voteCellCountsAccessibleLabel(option));
        }
        return parts.filter(Boolean).join(". ");
      },
      voteCellMenuAccessibleLabel(day, row, option) {
        const parts = [];
        const groupLabel = this.voteGroupAccessibleLabel(day, row);
        if (groupLabel) {
          parts.push(groupLabel);
        }
        if (option) {
          parts.push(`${this.t("myVote")}: ${this.voteStatusLabel(this.voteValueForOption(option))}`);
        }
        return parts.filter(Boolean).join(". ");
      },
      voteSyncAnnouncement(votes) {
        const normalizedVotes = Array.isArray(votes) ? votes : [];
        if (!normalizedVotes.length) {
          return "";
        }
        if (normalizedVotes.length === 1) {
          const status = this.normalizeVoteValue(normalizedVotes[0] && normalizedVotes[0].status);
          if (!status) {
            return this.t("voteCleared");
          }
          return this.formatTemplate(this.t("voteSavedStatus"), {
            status: this.voteStatusLabel(status)
          });
        }
        return this.t("votesSaved");
      },
      visibleVoteCellEntries() {
        const entries = [];
        for (const week of this.calendarWeeks) {
          const blocks = this.weekBlocksForWeek(week);
          for (const block of blocks) {
            const rows = this.filteredRowsForBlock(week, block);
            for (let rowIndex = 0; rowIndex < rows.length; rowIndex += 1) {
              const row = rows[rowIndex];
              for (let dayIndex = 0; dayIndex < block.days.length; dayIndex += 1) {
                const day = block.days[dayIndex];
                const option = row && row.cells ? row.cells[day.key] : null;
                if (!option || !Number.isInteger(option.id)) {
                  continue;
                }
                entries.push({
                  week,
                  block,
                  row,
                  day,
                  rowIndex,
                  dayIndex,
                  option
                });
              }
            }
          }
        }
        return entries;
      },
      firstVisibleVoteCellId() {
        const firstEntry = this.visibleVoteCellEntries()[0];
        return firstEntry && firstEntry.option ? firstEntry.option.id : null;
      },
      findVisibleVoteCellEntry(optionOrId) {
        const optionId = typeof optionOrId === "object"
          ? Number(optionOrId && optionOrId.id)
          : Number(optionOrId);
        if (!Number.isInteger(optionId)) {
          return null;
        }
        return this.visibleVoteCellEntries().find((entry) => entry.option.id === optionId) || null;
      },
      currentActiveVoteCellId() {
        const activeId = Number(this.activeVoteCellId);
        if (Number.isInteger(activeId) && this.findVisibleVoteCellEntry(activeId)) {
          return activeId;
        }
        return this.firstVisibleVoteCellId();
      },
      syncActiveVoteCell() {
        const nextActiveId = this.currentActiveVoteCellId();
        const normalizedActiveId = Number.isInteger(nextActiveId) ? nextActiveId : "";
        if (this.activeVoteCellId !== normalizedActiveId) {
          this.activeVoteCellId = normalizedActiveId;
        }
        if (this.bulkMenu && this.bulkMenu.type === "cell" && !this.findVisibleVoteCellEntry(this.bulkMenu.key)) {
          this.closeVoteMenus();
        }
      },
      setActiveVoteCell(optionOrId) {
        const optionId = typeof optionOrId === "object"
          ? Number(optionOrId && optionOrId.id)
          : Number(optionOrId);
        if (!Number.isInteger(optionId)) {
          this.syncActiveVoteCell();
          return;
        }
        this.activeVoteCellId = optionId;
      },
      voteCellTabIndex(option) {
        if (!option || !Number.isInteger(option.id)) {
          return -1;
        }
        const activeId = this.currentActiveVoteCellId();
        return activeId === option.id ? 0 : -1;
      },
      focusVoteCell(optionOrId) {
        const triggerId = this.voteCellTriggerId(optionOrId);
        if (!triggerId) {
          return;
        }
        const trigger = document.getElementById(triggerId);
        if (trigger && typeof trigger.focus === "function") {
          trigger.focus();
        }
      },
      openVoteCellMenu(option, options = {}) {
        if (!option || !Number.isInteger(option.id) || !this.canVoteInPoll) {
          return;
        }
        const focusStatus = Object.prototype.hasOwnProperty.call(options, "focusStatus")
          ? options.focusStatus
          : this.voteValueForOption(option);
        this.setActiveVoteCell(option.id);
        this.voteCellMenuPreview = {
          optionId: option.id,
          status: this.isVoteStatus(focusStatus) ? focusStatus : ""
        };
        this.openBulkMenu("cell", this.voteCellMenuScopeKey(), option.id, {
          focusStatus
        });
      },
      previewVoteCellMenuStatus(option, status) {
        if (!option || !Number.isInteger(option.id) || !this.isVoteCellMenuOpen(option)) {
          return;
        }
        this.voteCellMenuPreview = {
          optionId: option.id,
          status: this.isVoteStatus(status) ? status : ""
        };
      },
      handleVoteCellMenuKeydown(event, option) {
        if (!option || !Number.isInteger(option.id)) {
          return;
        }
        this.handleBulkMenuKeydown(event, "cell", this.voteCellMenuScopeKey(), option.id);
      },
      async chooseVoteCellMenuStatus(option, status) {
        if (!option || !Number.isInteger(option.id) || !this.canVoteInPoll) {
          return;
        }
        const normalizedStatus = this.isVoteStatus(status) ? status : "";
        this.closeVoteMenus({ restoreFocus: true });
        await this.applyVotes([option.id], normalizedStatus);
      },
      voteCellStatusFromClickEvent(event) {
        if (!event || Number(event.detail) === 0) {
          return "";
        }
        const target = event.target instanceof Element ? event.target : null;
        const segment = target ? target.closest("[data-vote-segment-status]") : null;
        const status = segment ? segment.getAttribute("data-vote-segment-status") : "";
        return this.isVoteStatus(status) ? status : "";
      },
      handleVoteCellTriggerClick(event, option) {
        if (!option || !Number.isInteger(option.id) || !this.canVoteInPoll) {
          return;
        }
        this.setActiveVoteCell(option.id);
        if (Number(event && event.detail) === 0 && this.isVoteCellMenuOpen(option)) {
          return;
        }
        const pointerStatus = this.voteCellStatusFromClickEvent(event);
        if (pointerStatus) {
          void this.setVoteStatus(option, pointerStatus);
          return;
        }
        if (this.isVoteCellMenuOpen(option)) {
          this.closeVoteMenus({ restoreFocus: true });
          return;
        }
        this.openVoteCellMenu(option);
      },
      findBlockVoteCellEntry(week, block, rowIndex, dayIndex) {
        if (!week || !block) {
          return null;
        }
        const rows = this.filteredRowsForBlock(week, block);
        if (rowIndex < 0 || rowIndex >= rows.length || dayIndex < 0 || dayIndex >= block.days.length) {
          return null;
        }
        const row = rows[rowIndex];
        const day = block.days[dayIndex];
        const option = row && row.cells ? row.cells[day.key] : null;
        if (!option || !Number.isInteger(option.id)) {
          return null;
        }
        return {
          week,
          block,
          row,
          day,
          rowIndex,
          dayIndex,
          option
        };
      },
      findAdjacentVoteCellEntry(optionOrId, direction) {
        const currentEntry = this.findVisibleVoteCellEntry(optionOrId);
        if (!currentEntry) {
          return null;
        }

        if (direction === "home" || direction === "end") {
          let dayIndex = direction === "home" ? 0 : currentEntry.block.days.length - 1;
          const step = direction === "home" ? 1 : -1;
          while (dayIndex >= 0 && dayIndex < currentEntry.block.days.length) {
            const candidate = this.findBlockVoteCellEntry(
              currentEntry.week,
              currentEntry.block,
              currentEntry.rowIndex,
              dayIndex
            );
            if (candidate) {
              return candidate;
            }
            dayIndex += step;
          }
          return currentEntry;
        }

        const horizontalStep = direction === "left" ? -1 : direction === "right" ? 1 : 0;
        if (horizontalStep) {
          let dayIndex = currentEntry.dayIndex + horizontalStep;
          while (dayIndex >= 0 && dayIndex < currentEntry.block.days.length) {
            const candidate = this.findBlockVoteCellEntry(
              currentEntry.week,
              currentEntry.block,
              currentEntry.rowIndex,
              dayIndex
            );
            if (candidate) {
              return candidate;
            }
            dayIndex += horizontalStep;
          }
          return currentEntry;
        }

        const verticalStep = direction === "up" ? -1 : direction === "down" ? 1 : 0;
        if (verticalStep) {
          const rows = this.filteredRowsForBlock(currentEntry.week, currentEntry.block);
          let rowIndex = currentEntry.rowIndex + verticalStep;
          while (rowIndex >= 0 && rowIndex < rows.length) {
            const candidate = this.findBlockVoteCellEntry(
              currentEntry.week,
              currentEntry.block,
              rowIndex,
              currentEntry.dayIndex
            );
            if (candidate) {
              return candidate;
            }
            rowIndex += verticalStep;
          }
        }

        return currentEntry;
      },
      handleVoteCellTriggerKeydown(event, option) {
        if (!option || !Number.isInteger(option.id)) {
          return;
        }
        let direction = "";
        if ((event.key === "Enter" || event.key === " ") && this.canVoteInPoll) {
          event.preventDefault();
          if (this.isVoteCellMenuOpen(option)) {
            this.closeVoteMenus({ restoreFocus: true });
            return;
          }
          this.openVoteCellMenu(option);
          return;
        }
        if (event.key === "ArrowLeft") {
          direction = "left";
        } else if (event.key === "ArrowRight") {
          direction = "right";
        } else if (event.key === "ArrowUp") {
          direction = "up";
        } else if (event.key === "ArrowDown") {
          direction = "down";
        } else if (event.key === "Home") {
          direction = "home";
        } else if (event.key === "End") {
          direction = "end";
        } else if (event.key === "Escape" && this.isVoteCellMenuOpen(option)) {
          event.preventDefault();
          this.closeVoteMenus({ restoreFocus: true });
          return;
        } else {
          return;
        }

        event.preventDefault();
        const nextEntry = this.findAdjacentVoteCellEntry(option, direction);
        if (!nextEntry || !nextEntry.option || !Number.isInteger(nextEntry.option.id)) {
          return;
        }
        this.setActiveVoteCell(nextEntry.option.id);
        if (nextEntry.option.id !== option.id) {
          this.$nextTick(() => {
            this.focusVoteCell(nextEntry.option.id);
          });
        }
      },
      async setVoteStatus(option, status) {
        if (!option || !Number.isInteger(option.id)) {
          return;
        }
        if (!this.isVoteStatus(status)) {
          return;
        }
        if (!this.canVoteInPoll) {
          return;
        }
        const currentStatus = this.voteValueForOption(option);
        const nextStatus = nextVoteStatus(currentStatus, status);
        this.closeVoteMenus();
        await this.applyVotes([option.id], nextStatus);
      },
      resetVoteSyncState() {
        if (this._voteSyncTimer) {
          window.clearTimeout(this._voteSyncTimer);
          this._voteSyncTimer = null;
        }
        this._voteSyncQueuedWhileSaving = false;
        this._voteSyncGeneration = Number(this._voteSyncGeneration || 0) + 1;
        this._voteSyncPromise = null;
      },
      hasPendingVoteSyncChanges() {
        return this.voteSyncPayloadForSelectedPoll().length > 0;
      },
      voteSyncPayloadForSelectedPoll() {
        if (!this.selectedPoll || this.selectedPoll.is_closed || !Array.isArray(this.selectedPoll.options)) {
          return [];
        }
        const votes = [];
        for (const option of this.selectedPoll.options) {
          if (!option || !Number.isInteger(option.id)) {
            continue;
          }
          const confirmedValue = this.confirmedVoteValueForOption(option);
          const desiredValue = this.voteValueForOption(option);
          if (desiredValue === confirmedValue) {
            continue;
          }
          votes.push({
            option_id: option.id,
            status: desiredValue || null
          });
        }
        return votes;
      },
      scheduleVoteSync(delay = voteSyncDebounceMs) {
        if (!this.selectedPoll || this.selectedPoll.is_closed) {
          return;
        }
        if (this._voteSyncInFlight) {
          this._voteSyncQueuedWhileSaving = true;
          return;
        }
        if (this._voteSyncTimer) {
          window.clearTimeout(this._voteSyncTimer);
        }
        const generation = Number(this._voteSyncGeneration || 0);
        const pollId = String(this.selectedPoll.id || "");
        const waitMs = Math.max(0, Number(delay) || 0);
        this._voteSyncTimer = window.setTimeout(() => {
          this._voteSyncTimer = null;
          if (generation !== Number(this._voteSyncGeneration || 0)) {
            return;
          }
          if (!this.selectedPoll || this.selectedPoll.is_closed || String(this.selectedPoll.id || "") !== pollId) {
            return;
          }
          void this.flushVoteSync();
        }, waitMs);
      },
      rollbackFailedVoteSync(snapshotByOptionId) {
        if (!this.selectedPoll || !snapshotByOptionId || typeof snapshotByOptionId !== "object") {
          return;
        }
        const nextDraft = { ...this.voteDraft };
        for (const option of this.selectedPoll.options) {
          if (!option || !Number.isInteger(option.id)) {
            continue;
          }
          if (!Object.prototype.hasOwnProperty.call(snapshotByOptionId, option.id)) {
            continue;
          }
          const snapshotValue = this.normalizeVoteValue(snapshotByOptionId[option.id]);
          if (this.voteValueForOption(option) !== snapshotValue) {
            continue;
          }
          nextDraft[option.id] = this.confirmedVoteValueForOption(option);
        }
        this.voteDraft = nextDraft;
      },
      pollSummaryFromDetail(poll) {
        if (!poll || typeof poll !== "object") {
          return null;
        }
        return {
          id: poll.id,
          identifier: typeof poll.identifier === "string" ? poll.identifier : "",
          title: typeof poll.title === "string" ? poll.title : "",
          description: typeof poll.description === "string" ? poll.description : "",
          window_starts_at: poll.window_starts_at || "",
          window_ends_at: poll.window_ends_at || "",
          start_date: typeof poll.start_date === "string" ? poll.start_date : "",
          end_date: typeof poll.end_date === "string" ? poll.end_date : "",
          slot_minutes: Number.isInteger(poll.slot_minutes) ? poll.slot_minutes : 60,
          daily_start_hour: Number.isInteger(poll.daily_start_hour) ? poll.daily_start_hour : 0,
          daily_end_hour: Number.isInteger(poll.daily_end_hour) ? poll.daily_end_hour : 24,
          allowed_weekdays: Array.isArray(poll.allowed_weekdays) ? [...poll.allowed_weekdays] : [],
          timezone: typeof poll.timezone === "string" ? poll.timezone : "",
          is_closed: Boolean(poll.is_closed),
          created_at: poll.created_at || "",
          closed_at: poll.closed_at || null,
          creator: poll.creator || null,
          participant_count: Number.isInteger(poll.participant_count) ? poll.participant_count : 0,
          can_close: Boolean(poll.can_close),
          can_reopen: Boolean(poll.can_reopen),
          can_delete: Boolean(poll.can_delete),
          can_edit: Boolean(poll.can_edit)
        };
      },
      patchPollSummaryFromDetail(poll) {
        const summary = this.pollSummaryFromDetail(poll);
        if (!summary) {
          return;
        }
        const pollId = String(summary.id || "");
        const existingIndex = this.polls.findIndex((item) => String(item && item.id || "") === pollId);
        if (existingIndex >= 0) {
          const nextPolls = [...this.polls];
          nextPolls.splice(existingIndex, 1, summary);
          this.polls = nextPolls;
          return;
        }
        this.polls = [...this.polls, summary];
      },
      async refreshPollListOnReturnIfNeeded() {
        if (this.activeSection !== "list" || !this.pollListNeedsRefresh) {
          return;
        }
        await this.fetchPolls();
      },
      async waitForPendingVoteSync() {
        if (!this.selectedPoll || this.selectedPoll.is_closed) {
          return;
        }
        while (true) {
          if (this._voteSyncTimer) {
            window.clearTimeout(this._voteSyncTimer);
            this._voteSyncTimer = null;
          }
          if (this._voteSyncInFlight) {
            try {
              await (this._voteSyncPromise || Promise.resolve());
            } catch (_error) {
              // keep the current UI state and exit once the in-flight request settles
            }
            continue;
          }
          if (this.hasPendingVoteSyncChanges()) {
            await this.flushVoteSync();
            continue;
          }
          return;
        }
      },
      async flushVoteSync() {
        if (this._voteSyncInFlight || !this.selectedPoll || this.selectedPoll.is_closed) {
          return;
        }
        const votes = this.voteSyncPayloadForSelectedPoll();
        if (!votes.length) {
          return;
        }

        const pollId = String(this.selectedPoll.id || "");
        const generation = Number(this._voteSyncGeneration || 0);
        const snapshotByOptionId = {};
        for (const vote of votes) {
          snapshotByOptionId[vote.option_id] = this.normalizeVoteValue(vote.status);
        }

        this._voteSyncInFlight = true;
        this._voteSyncQueuedWhileSaving = false;
        const syncPromise = (async () => {
          const data = await apiFetch(`/api/polls/${pollId}/votes/`, {
            method: "PUT",
            body: { votes }
          });
          return data;
        })();
        this._voteSyncPromise = syncPromise;
        try {
          const data = await syncPromise;
          if (
            generation === Number(this._voteSyncGeneration || 0)
            && this.selectedPoll
            && String(this.selectedPoll.id || "") === pollId
          ) {
            this.selectedPoll = data.poll;
            this.applyVoteDraft({ preserveLocalChanges: true });
            this.announceVoteStatus(this.voteSyncAnnouncement(votes));
          }
          this.patchPollSummaryFromDetail(data.poll);
          this.pollListNeedsRefresh = true;
        } catch (error) {
          if (
            generation === Number(this._voteSyncGeneration || 0)
            && this.selectedPoll
            && String(this.selectedPoll.id || "") === pollId
          ) {
            this.rollbackFailedVoteSync(snapshotByOptionId);
          }
          this.setError(this.resolveError(error.payload, "Could not save vote."));
        } finally {
          this._voteSyncInFlight = false;
          if (this._voteSyncPromise === syncPromise) {
            this._voteSyncPromise = null;
          }
          if (generation !== Number(this._voteSyncGeneration || 0)) {
            const shouldResumeCurrentSync = this._voteSyncQueuedWhileSaving || this.hasPendingVoteSyncChanges();
            this._voteSyncQueuedWhileSaving = false;
            if (shouldResumeCurrentSync) {
              this.scheduleVoteSync(0);
            }
            return;
          }
          const shouldSyncAgain = this._voteSyncQueuedWhileSaving || this.hasPendingVoteSyncChanges();
          this._voteSyncQueuedWhileSaving = false;
          if (shouldSyncAgain) {
            this.scheduleVoteSync(0);
          }
        }
      },
      async applyVotes(optionIds, status) {
        if (!this.selectedPoll || this.selectedPoll.is_closed) {
          return;
        }

        const uniqueOptionIds = Array.from(
          new Set(
            (optionIds || [])
              .map((value) => Number(value))
              .filter((value) => Number.isInteger(value))
          )
        );
        if (!uniqueOptionIds.length) {
          return;
        }

        const normalizedStatus = this.isVoteStatus(status) ? status : "";
        await this.ensureAuthenticated(async () => {
          if (!this.selectedPoll || this.selectedPoll.is_closed) {
            return;
          }

          const idSet = new Set(uniqueOptionIds);
          const targetOptions = this.selectedPoll.options.filter((item) => idSet.has(item.id));
          if (!targetOptions.length) {
            return;
          }

          const nextDraft = { ...this.voteDraft };
          let changed = false;
          for (const option of targetOptions) {
            const previousStatus = this.voteValueForOption(option);
            if (previousStatus === normalizedStatus) {
              continue;
            }
            nextDraft[option.id] = normalizedStatus;
            changed = true;
          }

          if (!changed) {
            return;
          }

          this.voteDraft = nextDraft;
          this.scheduleVoteSync();
        });
      },
      openCalendarTimezoneSuggestions() {
        if (this.calendarTimezoneMode !== "custom") {
          return;
        }
        this.showCalendarTimezoneSuggestions = true;
        this.syncTimezoneSuggestionIndex("calendar");
      },
      selectCalendarTimezone(value) {
        this.calendarCustomTimezone = value;
        this.closeTimezoneSuggestions("calendar");
        this.savePreferredCalendarTimezonePreference();
      },
      handleCalendarTimezoneInput() {
        this.openCalendarTimezoneSuggestions();
      },
      handleCalendarTimezoneKeydown(event) {
        this.handleTimezoneKeydown(event, "calendar");
      },
      handleCalendarTimezoneBlur() {
        window.setTimeout(() => {
          this.normalizeCalendarTimezoneInput();
          this.savePreferredCalendarTimezonePreference();
          this.closeTimezoneSuggestions("calendar");
        }, 120);
      },
      normalizeCalendarTimezoneInput() {
        const raw = (this.calendarCustomTimezone || "").trim();
        const fallback = this.browserCalendarTimezone || this.pollCalendarTimezone;
        if (!raw) {
          this.calendarCustomTimezone = fallback;
          return;
        }
        const normalized = this.normalizeKnownTimeZone(raw);
        if (normalized) {
          this.calendarCustomTimezone = normalized;
        }
      },
      calendarTimezonePreferenceStorageKey() {
        return calendarTimezonePreferenceStorageKeyForSession(this.session);
      },
      loadPreferredCalendarTimezonePreference() {
        const key = this.calendarTimezonePreferenceStorageKey();
        if (!key) {
          return { mode: "poll", timezone: "" };
        }
        const raw = safeLocalStorageGetItem(key);
        return loadCalendarTimezonePreferenceValue(raw, (value) => this.normalizeKnownTimeZone(value));
      },
      savePreferredCalendarTimezonePreference() {
        if (!this.session || !this.session.authenticated || !this.session.identity) {
          return;
        }
        const key = this.calendarTimezonePreferenceStorageKey();
        if (!key) {
          return;
        }
        const serializedPreference = serializeCalendarTimezonePreference(
          this.calendarTimezoneMode,
          this.calendarCustomTimezone,
          this.showBrowserTimezoneOption,
          (value) => this.normalizeKnownTimeZone(value)
        );
        if (!serializedPreference) {
          return;
        }
        safeLocalStorageSetItem(key, serializedPreference);
      }
    };
  };
})();
