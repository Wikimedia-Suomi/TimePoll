(() => {
  const domains = window.TimePollAppDomains || (window.TimePollAppDomains = {});

  domains.createShellDomainMethods = function createShellDomainMethods({
    buildPollUrlState,
    errorMessages,
    extractPollIdFromSearch,
    languageMap,
    successFeedbackAutoCloseMs,
    translations
  }) {
    return {
      focusableElementsIn(root) {
        if (!root || typeof root.querySelectorAll !== "function") {
          return [];
        }
        return Array.from(
          root.querySelectorAll(
            "a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])"
          )
        ).filter((element) => element.getClientRects().length > 0);
      },
      focusAuthDialogInitialField() {
        this.$nextTick(() => {
          const input = this.$refs.authNameInput;
          if (input && typeof input.focus === "function") {
            input.focus();
          }
        });
      },
      focusElementIfPossible(element) {
        if (
          element
          && typeof element.focus === "function"
          && document.contains(element)
        ) {
          try {
            element.focus({ preventScroll: true });
          } catch (_error) {
            element.focus();
          }
          if (element.classList && typeof element.classList.add === "function") {
            element.classList.add("programmatic-focus-visible");
            const clearProgrammaticFocus = () => {
              element.classList.remove("programmatic-focus-visible");
            };
            element.addEventListener("blur", clearProgrammaticFocus, { once: true });
          }
          return true;
        }
        return false;
      },
      focusElementById(id) {
        if (!id) {
          return false;
        }
        return this.focusElementIfPossible(document.getElementById(id));
      },
      pollListButtons() {
        return Array.from(document.querySelectorAll("#section-panel-list .poll-item"));
      },
      focusPollListHeading() {
        return this.focusElementById("poll-list-heading");
      },
      focusCreatePollButton() {
        return this.focusElementById("open-create-poll");
      },
      focusPollListButtonByIndex(index) {
        const buttons = this.pollListButtons();
        if (!buttons.length) {
          return false;
        }
        const normalizedIndex = Math.min(Math.max(Number(index) || 0, 0), buttons.length - 1);
        return this.focusElementIfPossible(buttons[normalizedIndex]);
      },
      pollListButtonIndexForElement(element) {
        if (!element) {
          return -1;
        }
        return this.pollListButtons().findIndex((button) => button === element);
      },
      handlePollListHeadingKeydown(event) {
        if (this.activeSection !== "list" || event.altKey || event.ctrlKey || event.metaKey) {
          return;
        }
        if (event.key === "ArrowDown" || event.key === "ArrowRight" || event.key === "Home") {
          event.preventDefault();
          if (!this.focusPollListButtonByIndex(0)) {
            this.focusCreatePollButton();
          }
          return;
        }
        if (event.key === "End") {
          event.preventDefault();
          const buttons = this.pollListButtons();
          if (!buttons.length) {
            this.focusCreatePollButton();
            return;
          }
          this.focusPollListButtonByIndex(buttons.length - 1);
        }
      },
      handlePollListItemKeydown(event) {
        if (this.activeSection !== "list" || event.altKey || event.ctrlKey || event.metaKey) {
          return;
        }
        const currentTarget = event.currentTarget instanceof HTMLElement ? event.currentTarget : null;
        const currentIndex = this.pollListButtonIndexForElement(currentTarget);
        if (currentIndex < 0) {
          return;
        }
        if (event.key === "ArrowDown" || event.key === "ArrowRight") {
          event.preventDefault();
          this.focusPollListButtonByIndex(Math.min(currentIndex + 1, this.pollListButtons().length - 1));
          return;
        }
        if (event.key === "ArrowUp" || event.key === "ArrowLeft") {
          event.preventDefault();
          if (currentIndex === 0) {
            this.focusPollListHeading();
            return;
          }
          this.focusPollListButtonByIndex(currentIndex - 1);
          return;
        }
        if (event.key === "Home") {
          event.preventDefault();
          this.focusPollListButtonByIndex(0);
          return;
        }
        if (event.key === "End") {
          event.preventDefault();
          this.focusPollListButtonByIndex(this.pollListButtons().length - 1);
        }
      },
      focusSectionReturnTarget(section, focusId = "") {
        this.$nextTick(() => {
          if (!(focusId && this.focusElementById(focusId))) {
            this.focusSectionHeading(section);
          }
        });
      },
      pollListItemId(pollId) {
        return `poll-list-item-${this.bulkMenuIdPart(pollId)}`;
      },
      profileCreatedPollButtonId(pollId) {
        return `profile-created-open-poll-${this.bulkMenuIdPart(pollId)}`;
      },
      profileVoteOpenPollButtonId(vote) {
        const rawId = vote && (vote.id ?? vote.poll_option_id ?? vote.poll_id);
        return `profile-vote-open-poll-${this.bulkMenuIdPart(rawId)}`;
      },
      sectionHeadingId(section = this.activeSection) {
        const sectionHeadingById = {
          list: "poll-list-heading",
          create: "create-poll-heading",
          selected: "details-heading",
          profile: "profile-heading"
        };
        return sectionHeadingById[section] || "poll-list-heading";
      },
      focusSectionHeading(section = this.activeSection) {
        return this.focusElementById(this.sectionHeadingId(section));
      },
      goHomeFromCurrentSection() {
        if (this.activeSection === "create") {
          this.cancelCreate({ returnFocusId: "" });
          return;
        }
        this.setActiveSection("list", { forceFocus: true });
      },
      rememberProfileSectionReturn(options = {}) {
        const currentTarget = this.profileSectionReturn || {};
        const currentSection = this.activeSection === "profile"
          ? currentTarget.section
          : this.activeSection;
        const section = options.returnSection === "list" || options.returnSection === "create" || options.returnSection === "selected"
          ? options.returnSection
          : currentSection === "create" || currentSection === "selected"
            ? currentSection
            : "list";
        const focusId = typeof options.returnFocusId === "string"
          ? options.returnFocusId
          : section === "create"
            ? "poll-title"
            : section === "selected"
              ? "details-heading"
              : "poll-list-heading";
        this.profileSectionReturn = { section, focusId };
      },
      returnFromProfileSection() {
        const targetSection = this.profileSectionReturnSection;
        const focusId = this.profileSectionReturn && typeof this.profileSectionReturn.focusId === "string"
          ? this.profileSectionReturn.focusId
          : "";
        const shouldRestoreCreateFocus = targetSection === "create" && Boolean(focusId);
        this.setActiveSection(targetSection, {
          skipFocus: targetSection !== "create",
          forceFocus: true
        });
        if (targetSection !== "create" || shouldRestoreCreateFocus) {
          this.focusSectionReturnTarget(targetSection, focusId);
        }
      },
      rememberSelectedSectionReturn(options = {}) {
        const hasExplicitSection = options.returnSection === "list" || options.returnSection === "profile";
        const currentTarget = this.selectedSectionReturn || {};
        const section = hasExplicitSection
          ? options.returnSection
          : this.activeSection === "selected"
            ? (currentTarget.section === "profile" ? "profile" : "list")
            : this.activeSection === "profile"
              ? "profile"
              : "list";
        const focusId = typeof options.returnFocusId === "string"
          ? options.returnFocusId
          : this.activeSection === "selected"
            ? (typeof currentTarget.focusId === "string" ? currentTarget.focusId : "")
            : "";
        this.selectedSectionReturn = { section, focusId };
      },
      returnFromSelectedSection() {
        const targetSection = this.selectedSectionReturnSection;
        const focusId = this.selectedSectionReturn && typeof this.selectedSectionReturn.focusId === "string"
          ? this.selectedSectionReturn.focusId
          : "";
        this.setActiveSection(targetSection, { skipFocus: true, forceFocus: true });
        this.focusSectionReturnTarget(targetSection, focusId);
      },
      focusAuthSuccessTarget(returnFocusTarget, options = {}) {
        this.$nextTick(() => {
          if (this.focusElementIfPossible(returnFocusTarget)) {
            return;
          }
          const focusTopbarTarget = () => {
            const topbarTarget = document.querySelector(".auth-actions .auth-name-link, .auth-actions .secondary");
            return this.focusElementIfPossible(topbarTarget);
          };

          if (options.preferSectionTarget) {
            if (!this.focusSectionHeading()) {
              focusTopbarTarget();
            }
            return;
          }

          if (!focusTopbarTarget()) {
            this.focusSectionHeading();
          }
        });
      },
      closeAuthDialog(options = {}) {
        const restoreFocus = options.restoreFocus !== false;
        const clearPendingAction = options.clearPendingAction !== false;
        const returnFocusTarget = restoreFocus ? this._authDialogReturnFocus : null;
        if (clearPendingAction) {
          this.pendingAction = null;
        }
        this.showAuthDialog = false;
        this._authDialogReturnFocus = null;
        this.$nextTick(() => {
          if (
            returnFocusTarget
            && typeof returnFocusTarget.focus === "function"
            && document.contains(returnFocusTarget)
          ) {
            returnFocusTarget.focus();
          }
        });
      },
      focusEditTimezoneConfirmDialogInitialField() {
        this.$nextTick(() => {
          const button = this.$refs.editTimezoneConfirmButton;
          if (button && typeof button.focus === "function") {
            button.focus();
          }
        });
      },
      openEditTimezoneConfirmDialog(proposal) {
        this.pendingEditTimezoneAutoGrow = proposal;
        this._editTimezoneConfirmDialogReturnFocus = this.$refs.editTimezoneInput
          || document.getElementById("edit-timezone")
          || document.activeElement;
        this.showEditTimezoneConfirmDialog = true;
        this.focusEditTimezoneConfirmDialogInitialField();
      },
      closeEditTimezoneConfirmDialog(options = {}) {
        const restoreFocus = options.restoreFocus !== false;
        const clearProposal = options.clearProposal !== false;
        const returnFocusTarget = restoreFocus ? this._editTimezoneConfirmDialogReturnFocus : null;
        if (clearProposal) {
          this.pendingEditTimezoneAutoGrow = null;
        }
        this.showEditTimezoneConfirmDialog = false;
        this._editTimezoneConfirmDialogReturnFocus = null;
        this.$nextTick(() => {
          if (
            returnFocusTarget
            && typeof returnFocusTarget.focus === "function"
            && document.contains(returnFocusTarget)
          ) {
            returnFocusTarget.focus();
          }
        });
      },
      cancelEditTimezoneChangeConfirmation() {
        this.editAutoGrowNotice = "";
        this.closeEditTimezoneConfirmDialog();
        this.validateFormScope("edit");
      },
      handleEditTimezoneConfirmDialogKeydown(event) {
        if (!this.showEditTimezoneConfirmDialog) {
          return;
        }
        if (event.key === "Escape") {
          event.preventDefault();
          this.cancelEditTimezoneChangeConfirmation();
          return;
        }
        if (event.key !== "Tab") {
          return;
        }
        const focusable = this.focusableElementsIn(this.$refs.editTimezoneConfirmDialog);
        if (!focusable.length) {
          event.preventDefault();
          return;
        }
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      },
      handleAuthDialogKeydown(event) {
        if (!this.showAuthDialog) {
          return;
        }
        if (event.key === "Escape") {
          event.preventDefault();
          this.closeAuthDialog();
          return;
        }
        if (event.key !== "Tab") {
          return;
        }
        const focusable = this.focusableElementsIn(this.$refs.authDialog);
        if (!focusable.length) {
          event.preventDefault();
          return;
        }
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      },
      t(key) {
        const set = translations[this.language] || translations.en;
        return set[key] || translations.en[key] || key;
      },
      formatTemplate(template, replacements = {}) {
        if (typeof template !== "string" || !template) {
          return "";
        }
        let output = template;
        for (const [name, value] of Object.entries(replacements)) {
          const token = `{${name}}`;
          output = output.split(token).join(String(value ?? ""));
        }
        return output;
      },
      fieldValidationMessage(fieldKey, kind) {
        const templateByKind = {
          required: "validationRequired",
          invalid: "validationInvalid",
          tooLong: "validationTooLong"
        };
        const templateKey = templateByKind[kind] || "validationInvalid";
        return this.formatTemplate(this.t(templateKey), { field: this.t(fieldKey) });
      },
      pollIdFromCurrentUrl() {
        if (typeof window === "undefined") {
          return "";
        }
        return extractPollIdFromSearch(window.location.search || "");
      },
      setPollIdInCurrentUrl(pollId, options = {}) {
        if (typeof window === "undefined") {
          return;
        }
        const replace = Boolean(options.replace);
        const { normalizedPollId, nextUrl } = buildPollUrlState(window.location.href, pollId);
        const currentUrl = `${window.location.pathname}${window.location.search}${window.location.hash}`;
        if (nextUrl === currentUrl) {
          return;
        }
        const nextState = {
          ...(window.history.state || {}),
          id: normalizedPollId || null
        };
        if (replace) {
          window.history.replaceState(nextState, "", nextUrl);
        } else {
          window.history.pushState(nextState, "", nextUrl);
        }
      },
      async applyPollFromUrl(options = {}) {
        const pollId = this.pollIdFromCurrentUrl();
        if (!pollId) {
          this.setActiveSection("list", { skipUrlSync: true });
          return;
        }
        if (this.selectedPoll && String(this.selectedPoll.id) === pollId) {
          this.setActiveSection("selected", { skipUrlSync: true });
          return;
        }
        await this.openPoll(pollId, {
          syncUrl: true,
          replaceUrl: Boolean(options.replace),
          fromUrl: true
        });
      },
      setActiveSection(section, options = {}) {
        if (section !== "list" && section !== "create" && section !== "selected" && section !== "profile") {
          return;
        }
        const sectionChanged = this.activeSection !== section;
        this.activeSection = section;
        this.closeVoteMenus();
        if (section !== "selected") {
          this.isEditingPoll = false;
          this.editForm = null;
          this.editCommittedTimezone = "";
          this.showEditTimezoneConfirmDialog = false;
          this.pendingEditTimezoneAutoGrow = null;
          this.editAutoGrowNotice = "";
          this.isApplyingEditTimezoneAutoGrow = false;
          this.isApplyingEditTimezoneProgrammaticChange = false;
          if (!options.skipUrlSync) {
            this.setPollIdInCurrentUrl("", { replace: Boolean(options.replaceUrl) });
          }
        }
        this.$nextTick(() => {
          this.updateVisibleDayCount();
          if (options.skipFocus || (!sectionChanged && options.forceFocus !== true)) {
            return;
          }
          if (section === "create") {
            this.focusPollFormInitialField("create");
            return;
          }
          this.focusSectionHeading(section);
        });
        if (section === "list") {
          void this.refreshPollListOnReturnIfNeeded();
        }
      },
      clearSuccessFeedbackTimer() {
        if (this.successFeedbackTimerId !== null) {
          window.clearTimeout(this.successFeedbackTimerId);
          this.successFeedbackTimerId = null;
        }
      },
      scheduleSuccessFeedbackDismiss() {
        this.clearSuccessFeedbackTimer();
        if (!this.successMessage) {
          return;
        }
        this.successFeedbackTimerId = window.setTimeout(() => {
          this.successMessage = "";
          this.successFeedbackTimerId = null;
        }, successFeedbackAutoCloseMs);
      },
      setSuccess(message) {
        this.clearSuccessFeedbackTimer();
        this.successMessage = message;
        this.errorMessage = "";
        this.scheduleSuccessFeedbackDismiss();
      },
      setError(error) {
        this.clearSuccessFeedbackTimer();
        this.errorMessage = error;
        this.successMessage = "";
      },
      clearFeedback() {
        this.clearSuccessFeedbackTimer();
        this.errorMessage = "";
        this.successMessage = "";
      },
      announceVoteStatus(message) {
        const nextMessage = String(message || "").trim();
        this.voteStatusAnnouncement = "";
        if (!nextMessage) {
          return;
        }
        this.$nextTick(() => {
          this.voteStatusAnnouncement = nextMessage;
        });
      },
      resolveError(payload, fallback) {
        if (payload && payload.error && errorMessages[payload.error]) {
          return errorMessages[payload.error][this.language] || errorMessages[payload.error].en;
        }
        if (payload && payload.detail) {
          return payload.detail;
        }
        return fallback;
      },
      formatDate(value, timeZone) {
        if (!value) {
          return "";
        }
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
          return value;
        }
        const options = {
          dateStyle: "medium",
          timeStyle: "short"
        };
        if (timeZone) {
          options.timeZone = timeZone;
        }
        return new Intl.DateTimeFormat(languageMap[this.language] || "en-GB", options).format(date);
      },
      hourLabel(hour) {
        const normalized = Number(hour);
        if (normalized === 24) {
          return "24:00";
        }
        return `${String(normalized).padStart(2, "0")}:00`;
      },
      formatLocalizedList(values = []) {
        const items = Array.isArray(values)
          ? values.map((value) => String(value || "").trim()).filter(Boolean)
          : [];
        if (!items.length) {
          return "";
        }
        if (typeof Intl !== "undefined" && typeof Intl.ListFormat === "function") {
          return new Intl.ListFormat(languageMap[this.language] || "en-GB", {
            style: "long",
            type: "conjunction"
          }).format(items);
        }
        return items.join(", ");
      }
    };
  };
})();
