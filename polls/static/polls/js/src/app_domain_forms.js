(() => {
  const domains = window.TimePollAppDomains || (window.TimePollAppDomains = {});

  domains.createFormDomainMethods = function createFormDomainMethods({
    autoGrowScheduleForm,
    buildTimeZoneMeta,
    defaultCreateForm,
    editFormFromPoll,
    filterTimezoneSuggestionOptions,
    isValidTimeZoneName,
    parseIsoDateValue,
    pollFormFieldIds,
    pollFormFieldOrder,
    pollFormWeekdaySelectorByScope,
    toggleWeekdaySelection
  }) {
    return {
      fieldErrorId(scope, field) {
        return `${scope}-${String(field || "").replaceAll("_", "-")}-error`;
      },
      fieldHasValidationError(scope, field) {
        return Boolean((this.formErrors[scope] || {})[field]);
      },
      fieldAriaInvalid(scope, field) {
        return this.fieldHasValidationError(scope, field) ? "true" : null;
      },
      fieldDescribedBy(scope, field, describedByIds = []) {
        const ids = Array.isArray(describedByIds)
          ? describedByIds.filter(Boolean)
          : [describedByIds].filter(Boolean);
        if (this.hasFieldError(scope, field)) {
          ids.push(this.fieldErrorId(scope, field));
        }
        return ids.length ? ids.join(" ") : null;
      },
      focusPollField(scope, field) {
        if (field === "allowed_weekdays") {
          const weekdayInput = document.querySelector(pollFormWeekdaySelectorByScope[scope] || "");
          return this.focusElementIfPossible(weekdayInput);
        }
        const fieldIds = pollFormFieldIds[scope] || {};
        return this.focusElementById(fieldIds[field] || "");
      },
      firstInvalidPollField(errors) {
        for (const field of pollFormFieldOrder) {
          if (errors && errors[field]) {
            return field;
          }
        }
        return "";
      },
      focusFirstInvalidPollField(scope, errors) {
        const firstField = this.firstInvalidPollField(errors || this.formErrors[scope] || {});
        if (!firstField) {
          return;
        }
        this.$nextTick(() => {
          this.focusPollField(scope, firstField);
        });
      },
      focusPollFormInitialField(scope = "create") {
        const fieldIds = pollFormFieldIds[scope] || {};
        const primaryFieldId = fieldIds.title || "";
        const fallbackHeadingId = scope === "create" ? "create-poll-heading" : "details-heading";
        this.$nextTick(() => {
          if (!this.focusElementById(primaryFieldId)) {
            this.focusElementById(fallbackHeadingId);
          }
        });
      },
      resetFormValidation(scope = "create") {
        this.formErrors[scope] = {};
        this.formTouched[scope] = {};
        this.showAllFormErrors[scope] = false;
      },
      markFieldTouched(field, scope = "create") {
        const next = {
          ...(this.formTouched[scope] || {})
        };
        next[field] = true;
        this.formTouched[scope] = next;
      },
      resetCreateFormState() {
        this.closeTimezoneSuggestions("create");
        this.createForm = defaultCreateForm();
        this.resetFormValidation("create");
      },
      createFormHasUnsavedChanges() {
        const form = this.createForm || defaultCreateForm();
        const baseline = defaultCreateForm();
        const normalizeWeekdays = (values) => (Array.isArray(values) ? values : [])
          .map((value) => Number(value))
          .filter((value) => Number.isInteger(value) && value >= 0 && value <= 6)
          .sort((left, right) => left - right)
          .join(",");
        return (
          String(form.identifier || "") !== String(baseline.identifier || "")
          || String(form.title || "") !== String(baseline.title || "")
          || String(form.description || "") !== String(baseline.description || "")
          || String(form.start_date || "") !== String(baseline.start_date || "")
          || String(form.end_date || "") !== String(baseline.end_date || "")
          || Number(form.daily_start_hour) !== Number(baseline.daily_start_hour)
          || Number(form.daily_end_hour) !== Number(baseline.daily_end_hour)
          || normalizeWeekdays(form.allowed_weekdays) !== normalizeWeekdays(baseline.allowed_weekdays)
          || String(form.timezone || "").trim() !== String(baseline.timezone || "").trim()
        );
      },
      discardCreateDraftConfirmed() {
        if (!this.createFormHasUnsavedChanges()) {
          return true;
        }
        return window.confirm(this.t("discardCreateConfirm"));
      },
      openCreateSection(options = {}) {
        const requestedFocusId = typeof options.returnFocusId === "string" ? options.returnFocusId : "";
        const activeElementId = document.activeElement && typeof document.activeElement.id === "string"
          ? document.activeElement.id
          : "";
        this.createSectionReturnFocusId = requestedFocusId || activeElementId || "open-create-poll";
        this.setActiveSection("create", { forceFocus: true });
      },
      cancelCreate(options = {}) {
        if (!this.discardCreateDraftConfirmed()) {
          return false;
        }
        const requestedFocusId = typeof options.returnFocusId === "string" ? options.returnFocusId : null;
        const returnFocusId = requestedFocusId !== null
          ? requestedFocusId
          : this.createSectionReturnFocusId;
        this.clearFeedback();
        this.resetCreateFormState();
        this.setActiveSection("list", { skipFocus: true, forceFocus: true });
        this.focusSectionReturnTarget("list", returnFocusId);
        return true;
      },
      timezoneSuggestionOptions(scope = "create") {
        if (scope === "calendar") {
          return this.filteredCalendarTimezoneOptions;
        }
        if (scope === "edit") {
          return this.filteredEditTimezoneOptions;
        }
        return this.filteredTimezoneOptions;
      },
      timezoneInputValue(scope = "create") {
        if (scope === "calendar") {
          return this.calendarCustomTimezone;
        }
        if (scope === "edit") {
          return this.editForm && typeof this.editForm.timezone === "string"
            ? this.editForm.timezone
            : "";
        }
        return this.createForm.timezone;
      },
      timezoneSuggestionsOpen(scope = "create") {
        if (scope === "calendar") {
          return this.showCalendarTimezoneSuggestions;
        }
        if (scope === "edit") {
          return this.showEditTimezoneSuggestions;
        }
        return this.showTimezoneSuggestions;
      },
      buildFilteredTimezoneOptions(query = "") {
        return filterTimezoneSuggestionOptions(
          this.timezoneOptions,
          query,
          (timeZone) => this.timezoneMeta(timeZone)
        );
      },
      activeTimezoneSuggestionIdForScope(scope = "create") {
        const options = this.timezoneSuggestionOptions(scope);
        const activeIndex = this.timezoneSuggestionIndex(scope);
        if (
          !this.timezoneSuggestionsOpen(scope)
          || activeIndex < 0
          || activeIndex >= options.length
        ) {
          return "";
        }
        return this.timezoneSuggestionOptionId(scope, activeIndex);
      },
      timezoneSuggestionIndex(scope = "create") {
        if (scope === "calendar") {
          return this.activeCalendarTimezoneSuggestionIndex;
        }
        if (scope === "edit") {
          return this.activeEditTimezoneSuggestionIndex;
        }
        return this.activeTimezoneSuggestionIndex;
      },
      setTimezoneSuggestionIndex(scope = "create", index = -1) {
        const options = this.timezoneSuggestionOptions(scope);
        const nextIndex = options.length
          ? Math.min(Math.max(Number(index) || 0, 0), options.length - 1)
          : -1;
        if (scope === "calendar") {
          this.activeCalendarTimezoneSuggestionIndex = nextIndex;
        } else if (scope === "edit") {
          this.activeEditTimezoneSuggestionIndex = nextIndex;
        } else {
          this.activeTimezoneSuggestionIndex = nextIndex;
        }
        if (nextIndex >= 0) {
          this.$nextTick(() => {
            const option = document.getElementById(this.timezoneSuggestionOptionId(scope, nextIndex));
            if (option && typeof option.scrollIntoView === "function") {
              option.scrollIntoView({ block: "nearest" });
            }
          });
        }
      },
      syncTimezoneSuggestionIndex(scope = "create") {
        const options = this.timezoneSuggestionOptions(scope);
        if (!options.length) {
          this.setTimezoneSuggestionIndex(scope, -1);
          return;
        }
        const normalizedValue = String(this.timezoneInputValue(scope) || "").trim().toLowerCase();
        const matchedIndex = options.findIndex((item) => item.id.toLowerCase() === normalizedValue);
        this.setTimezoneSuggestionIndex(scope, matchedIndex >= 0 ? matchedIndex : 0);
      },
      moveTimezoneSuggestionIndex(scope = "create", delta = 1) {
        const options = this.timezoneSuggestionOptions(scope);
        if (!options.length) {
          return;
        }
        const currentIndex = this.timezoneSuggestionIndex(scope);
        const baseIndex = currentIndex >= 0 ? currentIndex : 0;
        const nextIndex = (baseIndex + delta + options.length) % options.length;
        this.setTimezoneSuggestionIndex(scope, nextIndex);
      },
      timezoneSuggestionOptionId(scope = "create", index = 0) {
        return `${scope}-timezone-suggestion-${index}`;
      },
      selectActiveTimezoneSuggestion(scope = "create") {
        const options = this.timezoneSuggestionOptions(scope);
        const index = this.timezoneSuggestionIndex(scope);
        if (index < 0 || index >= options.length) {
          return;
        }
        const value = options[index].id;
        if (scope === "calendar") {
          this.selectCalendarTimezone(value);
        } else {
          this.selectTimezone(value, scope);
        }
      },
      closeTimezoneSuggestions(scope = "create") {
        if (scope === "calendar") {
          this.showCalendarTimezoneSuggestions = false;
          this.activeCalendarTimezoneSuggestionIndex = -1;
        } else if (scope === "edit") {
          this.showEditTimezoneSuggestions = false;
          this.activeEditTimezoneSuggestionIndex = -1;
        } else {
          this.showTimezoneSuggestions = false;
          this.activeTimezoneSuggestionIndex = -1;
        }
      },
      handleTimezoneKeydown(event, scope = "create") {
        const hasOptions = this.timezoneSuggestionOptions(scope).length > 0;
        if (event.key === "ArrowDown") {
          event.preventDefault();
          if (scope === "calendar") {
            this.openCalendarTimezoneSuggestions();
          } else if (scope === "edit") {
            this.openTimezoneSuggestions("edit");
          } else {
            this.openTimezoneSuggestions();
          }
          if (hasOptions) {
            this.moveTimezoneSuggestionIndex(scope, 1);
          }
          return;
        }
        if (event.key === "ArrowUp") {
          event.preventDefault();
          if (scope === "calendar") {
            this.openCalendarTimezoneSuggestions();
          } else if (scope === "edit") {
            this.openTimezoneSuggestions("edit");
          } else {
            this.openTimezoneSuggestions();
          }
          if (hasOptions) {
            this.moveTimezoneSuggestionIndex(scope, -1);
          }
          return;
        }
        if (event.key === "Home" && hasOptions) {
          event.preventDefault();
          this.setTimezoneSuggestionIndex(scope, 0);
          return;
        }
        if (event.key === "End" && hasOptions) {
          event.preventDefault();
          this.setTimezoneSuggestionIndex(scope, this.timezoneSuggestionOptions(scope).length - 1);
          return;
        }
        if (event.key === "Enter" && hasOptions) {
          const isOpen = scope === "calendar"
            ? this.showCalendarTimezoneSuggestions
            : scope === "edit"
              ? this.showEditTimezoneSuggestions
              : this.showTimezoneSuggestions;
          if (isOpen) {
            event.preventDefault();
            this.selectActiveTimezoneSuggestion(scope);
          }
          return;
        }
        if (event.key === "Escape") {
          const isOpen = scope === "calendar"
            ? this.showCalendarTimezoneSuggestions
            : scope === "edit"
              ? this.showEditTimezoneSuggestions
              : this.showTimezoneSuggestions;
          if (isOpen) {
            event.preventDefault();
            this.closeTimezoneSuggestions(scope);
          }
          return;
        }
        if (event.key === "Tab") {
          this.closeTimezoneSuggestions(scope);
        }
      },
      pollOptionHasVotes(option) {
        return (
          this.optionCount(option, "yes") > 0
          || this.optionCount(option, "no") > 0
          || this.optionCount(option, "maybe") > 0
        );
      },
      editVoteAutoGrowBounds() {
        const dateBounds = this.editVotedDateBounds || {};
        const hourBounds = this.editVotedHourBounds || {};
        const lockedWeekdays = Array.isArray(this.editLockedWeekdayValues)
          ? [...this.editLockedWeekdayValues]
          : [];
        return {
          earliestDay: dateBounds.earliestDay || "",
          latestDay: dateBounds.latestDay || "",
          earliestHour: Number.isInteger(hourBounds.earliestHour) ? hourBounds.earliestHour : null,
          minEndHour: Number.isInteger(hourBounds.minEndHour) ? hourBounds.minEndHour : null,
          lockedWeekdays,
          hasVotes: Boolean(dateBounds.hasVotes || hourBounds.hasVotes || lockedWeekdays.length)
        };
      },
      buildEditTimezoneAutoGrowProposal(previousTimezone, nextTimezone) {
        if (!this.isEditingPoll || !this.editForm) {
          return null;
        }

        const votedBounds = this.editVoteAutoGrowBounds();
        if (!nextTimezone || !votedBounds.hasVotes) {
          return null;
        }

        const currentForm = {
          start_date: String(this.editForm.start_date || "").trim(),
          end_date: String(this.editForm.end_date || "").trim(),
          daily_start_hour: this.editForm.daily_start_hour,
          daily_end_hour: this.editForm.daily_end_hour,
          allowed_weekdays: Array.isArray(this.editForm.allowed_weekdays)
            ? [...this.editForm.allowed_weekdays]
            : []
        };

        const result = autoGrowScheduleForm(this.editForm, votedBounds);
        const nextForm = result && typeof result === "object" ? result.nextForm : null;
        const changedFields = result && Array.isArray(result.changedFields) ? result.changedFields : [];
        if (!nextForm || !changedFields.length) {
          return null;
        }

        return {
          previousTimezone,
          nextTimezone,
          changedFields,
          nextForm: {
            timezone: nextTimezone,
            start_date: String(nextForm.start_date || "").trim(),
            end_date: String(nextForm.end_date || "").trim(),
            daily_start_hour: nextForm.daily_start_hour,
            daily_end_hour: nextForm.daily_end_hour,
            allowed_weekdays: Array.isArray(nextForm.allowed_weekdays)
              ? [...nextForm.allowed_weekdays]
              : []
          },
          startDateChange: changedFields.includes("start_date")
            ? {
                from: currentForm.start_date,
                to: String(nextForm.start_date || "").trim()
              }
            : null,
          endDateChange: changedFields.includes("end_date")
            ? {
                from: currentForm.end_date,
                to: String(nextForm.end_date || "").trim()
              }
            : null,
          startHourChange: changedFields.includes("daily_start_hour")
            ? {
                from: currentForm.daily_start_hour,
                to: nextForm.daily_start_hour
              }
            : null,
          endHourChange: changedFields.includes("daily_end_hour")
            ? {
                from: currentForm.daily_end_hour,
                to: nextForm.daily_end_hour
              }
            : null,
          weekdayChange: changedFields.includes("allowed_weekdays")
            ? {
                from: [...currentForm.allowed_weekdays],
                to: Array.isArray(nextForm.allowed_weekdays)
                  ? [...nextForm.allowed_weekdays]
                  : []
              }
            : null
        };
      },
      commitEditTimezoneChange() {
        if (!this.isEditingPoll || !this.editForm) {
          this.editAutoGrowNotice = "";
          return;
        }

        const rawTimeZone = String(this.editForm.timezone || "").trim();
        const normalizedTimeZone = this.normalizeKnownTimeZone(rawTimeZone);
        const previousTimezone = String(this.editCommittedTimezone || "").trim();

        if (normalizedTimeZone && rawTimeZone !== normalizedTimeZone) {
          this.isApplyingEditTimezoneProgrammaticChange = true;
          try {
            this.editForm.timezone = normalizedTimeZone;
          } finally {
            this.isApplyingEditTimezoneProgrammaticChange = false;
          }
        }

        if (!normalizedTimeZone) {
          this.editAutoGrowNotice = "";
          this.handleFormFieldChange("timezone", "edit");
          return;
        }

        if (!previousTimezone || normalizedTimeZone === previousTimezone) {
          this.editCommittedTimezone = normalizedTimeZone;
          this.editAutoGrowNotice = "";
          this.handleFormFieldChange("timezone", "edit");
          return;
        }

        const proposal = this.buildEditTimezoneAutoGrowProposal(previousTimezone, normalizedTimeZone);
        if (!proposal) {
          this.editCommittedTimezone = normalizedTimeZone;
          this.editAutoGrowNotice = "";
          this.handleFormFieldChange("timezone", "edit");
          return;
        }

        this.isApplyingEditTimezoneProgrammaticChange = true;
        try {
          this.editForm.timezone = previousTimezone;
        } finally {
          this.isApplyingEditTimezoneProgrammaticChange = false;
        }
        this.editAutoGrowNotice = "";
        this.handleFormFieldChange("timezone", "edit");
        this.openEditTimezoneConfirmDialog(proposal);
      },
      confirmEditTimezoneChangeConfirmation() {
        const proposal = this.pendingEditTimezoneAutoGrow;
        if (!proposal || !this.editForm) {
          this.closeEditTimezoneConfirmDialog();
          return;
        }

        this.closeEditTimezoneConfirmDialog({ restoreFocus: false, clearProposal: false });
        this.pendingEditTimezoneAutoGrow = null;
        this.isApplyingEditTimezoneAutoGrow = true;
        this.isApplyingEditTimezoneProgrammaticChange = true;
        try {
          this.editForm.timezone = proposal.nextTimezone;
          this.editForm.start_date = String(proposal.nextForm.start_date || "").trim();
          this.editForm.end_date = String(proposal.nextForm.end_date || "").trim();
          this.editForm.daily_start_hour = proposal.nextForm.daily_start_hour;
          this.editForm.daily_end_hour = proposal.nextForm.daily_end_hour;
          this.editForm.allowed_weekdays = Array.isArray(proposal.nextForm.allowed_weekdays)
            ? [...proposal.nextForm.allowed_weekdays]
            : [];
        } finally {
          this.isApplyingEditTimezoneProgrammaticChange = false;
          this.isApplyingEditTimezoneAutoGrow = false;
        }

        this.editCommittedTimezone = proposal.nextTimezone;
        this.editAutoGrowNotice = this.t("editTimezoneAutoGrowNotice");
        this.handleFormFieldChange("timezone", "edit");
        this.$nextTick(() => {
          this.focusElementById("edit-timezone");
        });
      },
      pollOptionConflictsWithSchedule(option, form, startDate, endDate, allowedWeekdaysSet, timeZone) {
        if (!option || typeof option !== "object" || !option.starts_at) {
          return false;
        }

        const dateParts = this.timezoneDateParts(option.starts_at, timeZone);
        if (!dateParts) {
          return false;
        }

        const optionDate = parseIsoDateValue(dateParts.dayKey);
        if (!optionDate) {
          return false;
        }

        if (optionDate.getTime() < startDate.getTime() || optionDate.getTime() > endDate.getTime()) {
          return true;
        }

        const weekdayJs = optionDate.getUTCDay();
        const weekday = weekdayJs === 0 ? 6 : weekdayJs - 1;
        if (!allowedWeekdaysSet.has(weekday)) {
          return true;
        }

        const hourMatch = /^(\d{2}):(\d{2})$/.exec(dateParts.timeKey || "");
        if (!hourMatch) {
          return true;
        }
        const hour = Number(hourMatch[1]);
        const minute = Number(hourMatch[2]);
        if (!Number.isInteger(hour) || !Number.isInteger(minute) || minute !== 0) {
          return true;
        }

        if (hour < form.daily_start_hour || hour >= form.daily_end_hour) {
          return true;
        }

        return false;
      },
      hasScheduleConflictWithVotes(form) {
        if (!this.selectedPoll || !Array.isArray(this.selectedPoll.options) || !form) {
          return false;
        }

        const timeZone = String(form.timezone || "").trim();
        const startDate = parseIsoDateValue(String(form.start_date || "").trim());
        const endDate = parseIsoDateValue(String(form.end_date || "").trim());

        if (
          !timeZone ||
          !isValidTimeZoneName(timeZone) ||
          !startDate ||
          !endDate ||
          !Number.isInteger(form.daily_start_hour) ||
          !Number.isInteger(form.daily_end_hour)
        ) {
          return false;
        }

        const allowedWeekdaysSet = new Set(
          (Array.isArray(form.allowed_weekdays) ? form.allowed_weekdays : [])
            .map((value) => Number(value))
            .filter((value) => Number.isInteger(value) && value >= 0 && value <= 6)
        );
        if (!allowedWeekdaysSet.size) {
          return false;
        }

        for (const option of this.selectedPoll.options) {
          if (!this.pollOptionHasVotes(option)) {
            continue;
          }
          if (this.pollOptionConflictsWithSchedule(option, form, startDate, endDate, allowedWeekdaysSet, timeZone)) {
            return true;
          }
        }
        return false;
      },
      buildPollFormErrors(form, scope = "create") {
        const errors = {};
        if (!form) {
          return errors;
        }

        const title = String(form.title || "").trim();
        const identifier = String(form.identifier || "").trim();
        const startDateRaw = String(form.start_date || "").trim();
        const endDateRaw = String(form.end_date || "").trim();
        const timezoneName = String(form.timezone || "").trim();

        if (!title) {
          errors.title = this.fieldValidationMessage("title", "required");
        } else if (title.length > 160) {
          errors.title = this.fieldValidationMessage("title", "tooLong");
        }

        if (identifier) {
          if (identifier.length > 80 || !/^[A-Za-z0-9_]+$/.test(identifier)) {
            errors.identifier = this.resolveError({ error: "invalid_poll_identifier" }, "");
          }
        }

        const startDate = parseIsoDateValue(startDateRaw);
        const endDate = parseIsoDateValue(endDateRaw);

        if (!startDateRaw) {
          errors.start_date = this.fieldValidationMessage("startDate", "required");
        } else if (!startDate) {
          errors.start_date = this.resolveError(
            { error: "invalid_date" },
            this.fieldValidationMessage("startDate", "invalid")
          );
        }

        if (!endDateRaw) {
          errors.end_date = this.fieldValidationMessage("endDate", "required");
        } else if (!endDate) {
          errors.end_date = this.resolveError(
            { error: "invalid_date" },
            this.fieldValidationMessage("endDate", "invalid")
          );
        }

        if (startDate && endDate && endDate.getTime() < startDate.getTime()) {
          const rangeError = this.resolveError({ error: "invalid_date_range" }, "");
          errors.start_date = rangeError;
          errors.end_date = rangeError;
        }

        if (!Number.isInteger(form.daily_start_hour)) {
          errors.daily_start_hour = this.fieldValidationMessage("dailyStartHour", "required");
        } else if (form.daily_start_hour < 0 || form.daily_start_hour > 23) {
          errors.daily_start_hour = this.fieldValidationMessage("dailyStartHour", "invalid");
        }

        if (!Number.isInteger(form.daily_end_hour)) {
          errors.daily_end_hour = this.fieldValidationMessage("dailyEndHour", "required");
        } else if (form.daily_end_hour < 1 || form.daily_end_hour > 24) {
          errors.daily_end_hour = this.fieldValidationMessage("dailyEndHour", "invalid");
        }

        if (
          Number.isInteger(form.daily_start_hour) &&
          Number.isInteger(form.daily_end_hour) &&
          form.daily_end_hour <= form.daily_start_hour
        ) {
          const hoursError = this.resolveError({ error: "invalid_daily_hours" }, "");
          errors.daily_start_hour = hoursError;
          errors.daily_end_hour = hoursError;
        }

        if (!Array.isArray(form.allowed_weekdays) || form.allowed_weekdays.length === 0) {
          errors.allowed_weekdays = this.resolveError({ error: "invalid_weekdays" }, "");
        }

        if (!timezoneName) {
          errors.timezone = this.fieldValidationMessage("timezone", "required");
        } else if (!isValidTimeZoneName(timezoneName)) {
          errors.timezone = this.resolveError({ error: "invalid_timezone" }, "");
        }

        if (
          scope === "edit" &&
          Object.keys(errors).length === 0 &&
          this.hasScheduleConflictWithVotes(form)
        ) {
          const conflictError = this.resolveError({ error: "schedule_conflicts_with_votes" }, "");
          errors.timezone = conflictError;
          errors.start_date = conflictError;
          errors.end_date = conflictError;
          errors.daily_start_hour = conflictError;
          errors.daily_end_hour = conflictError;
          errors.allowed_weekdays = conflictError;
        }

        return errors;
      },
      validateFormScope(scope = "create") {
        const form = this.formForScope(scope);
        const errors = this.buildPollFormErrors(form, scope);
        this.formErrors[scope] = errors;
        return errors;
      },
      backendErrorFields(errorCode) {
        if (errorCode === "invalid_title") {
          return ["title"];
        }
        if (errorCode === "invalid_poll_identifier" || errorCode === "poll_identifier_taken") {
          return ["identifier"];
        }
        if (errorCode === "invalid_timezone") {
          return ["timezone"];
        }
        if (errorCode === "invalid_date_range" || errorCode === "invalid_date") {
          return ["start_date", "end_date"];
        }
        if (errorCode === "invalid_daily_hours") {
          return ["daily_start_hour", "daily_end_hour"];
        }
        if (errorCode === "invalid_weekdays") {
          return ["allowed_weekdays"];
        }
        if (errorCode === "too_many_options") {
          return ["start_date", "end_date", "daily_start_hour", "daily_end_hour", "allowed_weekdays"];
        }
        if (errorCode === "schedule_conflicts_with_votes") {
          return ["timezone", "start_date", "end_date", "daily_start_hour", "daily_end_hour", "allowed_weekdays"];
        }
        return [];
      },
      applyBackendFormError(scope, payload) {
        if (!payload || typeof payload !== "object" || typeof payload.error !== "string") {
          return false;
        }
        const fields = this.backendErrorFields(payload.error);
        if (!fields.length) {
          return false;
        }
        const message = this.resolveError(payload, payload.detail || this.t("validationInvalidValue"));
        const nextErrors = {
          ...(this.formErrors[scope] || {})
        };
        const nextTouched = {
          ...(this.formTouched[scope] || {})
        };
        for (const field of fields) {
          nextErrors[field] = message;
          nextTouched[field] = true;
        }
        this.formErrors[scope] = nextErrors;
        this.formTouched[scope] = nextTouched;
        this.showAllFormErrors[scope] = true;
        return true;
      },
      handleFormFieldChange(field, scope = "create") {
        this.markFieldTouched(field, scope);
        this.validateFormScope(scope);
      },
      fieldError(scope, field) {
        const errors = this.formErrors[scope] || {};
        const message = errors[field];
        if (!message) {
          return "";
        }
        if (this.showAllFormErrors[scope]) {
          return message;
        }
        const touched = this.formTouched[scope] || {};
        return touched[field] ? message : "";
      },
      hasFieldError(scope, field) {
        return Boolean(this.fieldError(scope, field));
      },
      formatWeekdaySelectionSummary(values = []) {
        const labelByValue = new Map(
          this.weekdayOptions.map((weekday) => [Number(weekday.value), weekday.label])
        );
        const labels = (Array.isArray(values) ? values : [])
          .map((value) => labelByValue.get(Number(value)))
          .filter(Boolean);
        return this.formatLocalizedList(labels);
      },
      editTimezoneConfirmDescriptionText() {
        const proposal = this.pendingEditTimezoneAutoGrow;
        if (!proposal) {
          return "";
        }
        return this.formatTemplate(this.t("editTimezoneConfirmDescription"), {
          from: this.timezoneDisplay(proposal.previousTimezone),
          to: this.timezoneDisplay(proposal.nextTimezone)
        });
      },
      editTimezoneAutoGrowProposalSummaryLines() {
        const proposal = this.pendingEditTimezoneAutoGrow;
        if (!proposal) {
          return [];
        }
        const lines = [];
        if (proposal.startDateChange) {
          lines.push(
            `${this.t("startDate")}: ${this.formatDayLongLabel(proposal.startDateChange.from)} -> ${this.formatDayLongLabel(proposal.startDateChange.to)}`
          );
        }
        if (proposal.endDateChange) {
          lines.push(
            `${this.t("endDate")}: ${this.formatDayLongLabel(proposal.endDateChange.from)} -> ${this.formatDayLongLabel(proposal.endDateChange.to)}`
          );
        }
        if (proposal.startHourChange) {
          lines.push(
            `${this.t("dailyStartHour")}: ${this.hourLabel(proposal.startHourChange.from)} -> ${this.hourLabel(proposal.startHourChange.to)}`
          );
        }
        if (proposal.endHourChange) {
          lines.push(
            `${this.t("dailyEndHour")}: ${this.hourLabel(proposal.endHourChange.from)} -> ${this.hourLabel(proposal.endHourChange.to)}`
          );
        }
        if (proposal.weekdayChange) {
          lines.push(
            `${this.t("allowedWeekdays")}: ${this.formatWeekdaySelectionSummary(proposal.weekdayChange.from)} -> ${this.formatWeekdaySelectionSummary(proposal.weekdayChange.to)}`
          );
        }
        return lines;
      },
      formForScope(scope = "create") {
        if (scope === "edit") {
          return this.editForm;
        }
        return this.createForm;
      },
      isWeekdaySelected(weekday, scope = "create") {
        const form = this.formForScope(scope);
        if (!form || !Array.isArray(form.allowed_weekdays)) {
          return false;
        }
        return form.allowed_weekdays.includes(weekday);
      },
      isWeekdayRemovalLocked(weekday, scope = "create") {
        if (scope !== "edit") {
          return false;
        }
        return this.isWeekdaySelected(weekday, scope) && this.editLockedWeekdayValues.includes(weekday);
      },
      toggleWeekday(weekday, scope = "create") {
        const form = this.formForScope(scope);
        if (!form || !Array.isArray(form.allowed_weekdays)) {
          return;
        }
        if (this.isWeekdayRemovalLocked(weekday, scope)) {
          return;
        }
        form.allowed_weekdays = toggleWeekdaySelection(form.allowed_weekdays, weekday);
      },
      validatePollForm(form) {
        if (!form) {
          return this.t("validationFormInvalid");
        }
        const scope = form === this.editForm ? "edit" : "create";
        const errors = this.validateFormScope(scope);
        this.showAllFormErrors[scope] = true;
        const firstField = this.firstInvalidPollField(errors);
        if (firstField) {
          return errors[firstField];
        }
        return "";
      },
      pollPayloadFromForm(form) {
        return {
          identifier: String(form.identifier || "").trim(),
          title: String(form.title || "").trim(),
          description: String(form.description || "").trim(),
          start_date: String(form.start_date || "").trim(),
          end_date: String(form.end_date || "").trim(),
          daily_start_hour: form.daily_start_hour,
          daily_end_hour: form.daily_end_hour,
          allowed_weekdays: [...form.allowed_weekdays],
          timezone: String(form.timezone || "").trim()
        };
      },
      startEditingPoll() {
        if (!this.selectedPoll || !this.selectedPoll.can_edit) {
          return;
        }
        this.editForm = editFormFromPoll(this.selectedPoll);
        this.editCommittedTimezone = String(this.editForm.timezone || "").trim();
        this.closeTimezoneSuggestions("edit");
        this.showEditTimezoneConfirmDialog = false;
        this.pendingEditTimezoneAutoGrow = null;
        this.editAutoGrowNotice = "";
        this.isApplyingEditTimezoneAutoGrow = false;
        this.isApplyingEditTimezoneProgrammaticChange = false;
        this.resetFormValidation("edit");
        this.isEditingPoll = true;
        this.closeVoteMenus();
        this.focusPollFormInitialField("edit");
      },
      cancelEditingPoll() {
        this.closeTimezoneSuggestions("edit");
        this.showEditTimezoneConfirmDialog = false;
        this.pendingEditTimezoneAutoGrow = null;
        this.isEditingPoll = false;
        this.editForm = null;
        this.editCommittedTimezone = "";
        this.editAutoGrowNotice = "";
        this.isApplyingEditTimezoneAutoGrow = false;
        this.isApplyingEditTimezoneProgrammaticChange = false;
        this.resetFormValidation("edit");
      },
      timezoneMeta(timeZone) {
        if (!timeZone) {
          return "";
        }
        if (Object.prototype.hasOwnProperty.call(this.timezoneMetaCache, timeZone)) {
          return this.timezoneMetaCache[timeZone];
        }
        const meta = buildTimeZoneMeta(timeZone);
        this.timezoneMetaCache[timeZone] = meta;
        return meta;
      },
      timezoneDisplay(timeZone) {
        if (!timeZone) {
          return "";
        }
        const meta = this.timezoneMeta(timeZone);
        return meta ? `${timeZone} (${meta})` : timeZone;
      },
      normalizeKnownTimeZone(value) {
        const raw = String(value || "").trim();
        if (!raw) {
          return "";
        }
        if (isValidTimeZoneName(raw)) {
          return raw;
        }
        const matched = this.timezoneOptions.find((tz) => tz.toLowerCase() === raw.toLowerCase());
        if (matched && isValidTimeZoneName(matched)) {
          return matched;
        }
        return "";
      },
      openTimezoneSuggestions(scope = "create") {
        if (scope === "edit" && (!this.isEditingPoll || !this.editForm)) {
          return;
        }
        if (scope === "edit" && this.showEditTimezoneConfirmDialog) {
          return;
        }
        if (scope === "edit") {
          this.showEditTimezoneSuggestions = true;
          this.syncTimezoneSuggestionIndex("edit");
          return;
        }
        this.showTimezoneSuggestions = true;
        this.syncTimezoneSuggestionIndex("create");
      },
      selectTimezone(value, scope = "create") {
        if (scope === "edit") {
          if (!this.editForm) {
            return;
          }
          this.editForm.timezone = value;
          this.closeTimezoneSuggestions("edit");
          this.commitEditTimezoneChange();
          return;
        }
        this.createForm.timezone = value;
        this.handleFormFieldChange("timezone", "create");
        this.closeTimezoneSuggestions("create");
      },
      handleCreateTimezoneInput() {
        this.openTimezoneSuggestions();
        this.handleFormFieldChange("timezone", "create");
      },
      handleEditTimezoneInput() {
        this.openTimezoneSuggestions("edit");
      },
      handleCreateTimezoneKeydown(event) {
        this.handleTimezoneKeydown(event, "create");
      },
      handleEditTimezoneKeydown(event) {
        this.handleTimezoneKeydown(event, "edit");
      },
      handleTimezoneBlur(scope = "create") {
        window.setTimeout(() => {
          this.normalizeTimezoneInput(scope);
          if (scope === "edit") {
            this.commitEditTimezoneChange();
          } else {
            this.handleFormFieldChange("timezone", "create");
          }
          this.closeTimezoneSuggestions(scope);
        }, 120);
      },
      normalizeTimezoneInput(scope = "create") {
        const raw = scope === "edit"
          ? (this.editForm && typeof this.editForm.timezone === "string" ? this.editForm.timezone.trim() : "")
          : (this.createForm.timezone || "").trim();
        if (!raw) {
          return;
        }
        const matched = this.timezoneOptions.find((tz) => tz.toLowerCase() === raw.toLowerCase());
        if (matched) {
          if (scope === "edit") {
            if (this.editForm) {
              this.editForm.timezone = matched;
            }
          } else {
            this.createForm.timezone = matched;
          }
        }
      }
    };
  };
})();
