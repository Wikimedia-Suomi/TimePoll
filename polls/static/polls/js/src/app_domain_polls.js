(() => {
  const domains = window.TimePollAppDomains || (window.TimePollAppDomains = {});

  domains.createPollDomainMethods = function createPollDomainMethods({
    apiFetch,
    defaultCreateForm
  }) {
    return {
      async fetchPolls() {
        try {
          const data = await apiFetch("/api/polls/");
          this.polls = data.polls || [];
          this.pollListNeedsRefresh = false;
        } catch (error) {
          this.setError(this.resolveError(error.payload, "Could not load polls."));
        }
      },
      applyVoteDraft(options = {}) {
        const draft = {};
        const preserveLocalChanges = options.preserveLocalChanges === true;
        const previousDraft = preserveLocalChanges ? { ...this.voteDraft } : {};
        if (!this.selectedPoll) {
          this.voteDraft = draft;
          this.closeVoteMenus();
          return;
        }
        for (const option of this.selectedPoll.options) {
          const confirmedValue = this.confirmedVoteValueForOption(option);
          draft[option.id] = preserveLocalChanges && Object.prototype.hasOwnProperty.call(previousDraft, option.id)
            ? this.normalizeVoteValue(previousDraft[option.id], confirmedValue)
            : confirmedValue;
        }
        this.voteDraft = draft;
        this.closeVoteMenus();
      },
      async openPoll(pollId, options = {}) {
        const normalizedPollId = String(pollId || "").trim();
        if (!normalizedPollId) {
          return;
        }
        if (options.preserveFeedback !== true) {
          this.clearFeedback();
        }
        try {
          const data = await apiFetch(`/api/polls/${encodeURIComponent(normalizedPollId)}/`);
          this.resetVoteSyncState();
          this.selectedPoll = data.poll;
          const preference = this.loadPreferredCalendarTimezonePreference();
          const preferredTimezone = this.normalizeKnownTimeZone(preference.timezone);
          this.calendarCustomTimezone = preferredTimezone || this.browserCalendarTimezone;

          let nextMode = preference.mode;
          if (nextMode !== "poll" && nextMode !== "browser" && nextMode !== "custom") {
            nextMode = "poll";
          }
          if (nextMode === "browser" && !this.showBrowserTimezoneOption) {
            nextMode = "poll";
          }
          if (nextMode === "custom" && !preferredTimezone) {
            nextMode = "poll";
          }
          this.calendarTimezoneMode = nextMode;
          this.showCalendarTimezoneSuggestions = false;
          this.minYesVotesFilter = 0;
          this.rememberSelectedSectionReturn(options);
          this.setActiveSection("selected", { skipUrlSync: true, forceFocus: true });
          this.applyVoteDraft();
          if (options.syncUrl !== false) {
            this.setPollIdInCurrentUrl(this.selectedPoll.id, {
              replace: Boolean(options.replaceUrl)
            });
          }
        } catch (error) {
          this.setError(this.resolveError(error.payload, "Could not open poll."));
          if (options.fromUrl) {
            this.resetVoteSyncState();
            this.selectedPoll = null;
            this.voteDraft = {};
            this.setActiveSection("list", { skipUrlSync: true });
            this.setPollIdInCurrentUrl("", { replace: true });
          }
        }
      },
      async submitPoll() {
        await this.ensureAuthenticated(async () => {
          this.clearFeedback();
          const validationError = this.validatePollForm(this.createForm);
          if (validationError) {
            this.setError(validationError);
            this.focusFirstInvalidPollField("create");
            return;
          }

          try {
            const data = await apiFetch("/api/polls/", {
              method: "POST",
              body: this.pollPayloadFromForm(this.createForm)
            });

            this.createForm = defaultCreateForm();
            this.resetFormValidation("create");

            this.setSuccess(this.t("createdSuccess"));
            await this.fetchPolls();
            await this.openPoll(data.poll.id, {
              preserveFeedback: true,
              returnSection: "list",
              returnFocusId: this.pollListItemId(data.poll.id)
            });
          } catch (error) {
            const mappedToField = this.applyBackendFormError("create", error.payload);
            this.setError(this.resolveError(error.payload, "Could not create poll."));
            if (mappedToField) {
              this.focusFirstInvalidPollField("create");
            }
          }
        });
      },
      async submitPollEdit() {
        if (!this.selectedPoll || !this.editForm) {
          return;
        }

        await this.ensureAuthenticated(async () => {
          this.clearFeedback();
          if (!this.selectedPoll || !this.selectedPoll.can_edit || !this.editForm) {
            this.setError(this.resolveError({ error: "forbidden" }, ""));
            return;
          }

          const validationError = this.validatePollForm(this.editForm);
          if (validationError) {
            this.setError(validationError);
            this.focusFirstInvalidPollField("edit");
            return;
          }

          try {
            const data = await apiFetch(`/api/polls/${this.selectedPoll.id}/`, {
              method: "PUT",
              body: this.pollPayloadFromForm(this.editForm)
            });
            this.resetVoteSyncState();
            this.selectedPoll = data.poll;
            this.applyVoteDraft();
            this.isEditingPoll = false;
            this.editForm = null;
            this.resetFormValidation("edit");
            this.setSuccess(this.t("pollUpdatedSuccess"));
            await this.fetchPolls();
          } catch (error) {
            const mappedToField = this.applyBackendFormError("edit", error.payload);
            this.setError(this.resolveError(error.payload, "Could not update poll."));
            if (mappedToField) {
              this.focusFirstInvalidPollField("edit");
            }
          }
        });
      },
      async closeSelectedPoll() {
        if (!this.selectedPoll) {
          return;
        }

        await this.ensureAuthenticated(async () => {
          this.clearFeedback();
          try {
            const data = await apiFetch(`/api/polls/${this.selectedPoll.id}/close/`, {
              method: "POST"
            });
            this.resetVoteSyncState();
            this.selectedPoll = data.poll;
            this.isEditingPoll = false;
            this.editForm = null;
            this.applyVoteDraft();
            await this.fetchPolls();
            this.setSuccess(this.t("pollClosedSuccess"));
          } catch (error) {
            this.setError(this.resolveError(error.payload, "Could not close poll."));
          }
        });
      },
      async reopenSelectedPoll() {
        if (!this.selectedPoll) {
          return;
        }

        await this.ensureAuthenticated(async () => {
          this.clearFeedback();
          try {
            const data = await apiFetch(`/api/polls/${this.selectedPoll.id}/reopen/`, {
              method: "POST"
            });
            this.resetVoteSyncState();
            this.selectedPoll = data.poll;
            this.isEditingPoll = false;
            this.editForm = null;
            this.applyVoteDraft();
            await this.fetchPolls();
            this.setSuccess(this.t("pollReopenedSuccess"));
          } catch (error) {
            this.setError(this.resolveError(error.payload, "Could not reopen poll."));
          }
        });
      },
      async deleteSelectedPoll() {
        if (!this.selectedPoll) {
          return;
        }
        if (!window.confirm(this.t("confirmDeletePoll"))) {
          return;
        }

        await this.ensureAuthenticated(async () => {
          this.clearFeedback();
          try {
            const deletedPollId = String(this.selectedPoll.id || "").trim();
            await apiFetch(`/api/polls/${this.selectedPoll.id}/`, { method: "DELETE" });
            this.resetVoteSyncState();
            if (deletedPollId) {
              this.polls = Array.isArray(this.polls)
                ? this.polls.filter((poll) => String(poll && poll.id || "").trim() !== deletedPollId)
                : [];
              if (this.profileData && Array.isArray(this.profileData.created_polls)) {
                this.profileData = {
                  ...this.profileData,
                  created_polls: this.profileData.created_polls.filter(
                    (poll) => String(poll && poll.id || "").trim() !== deletedPollId
                  ),
                  votes: Array.isArray(this.profileData.votes)
                    ? this.profileData.votes.filter(
                        (vote) => String(vote && vote.poll && vote.poll.id || "").trim() !== deletedPollId
                      )
                    : this.profileData.votes
                };
              }
            }
            this.selectedPoll = null;
            this.isEditingPoll = false;
            this.editForm = null;
            this.voteDraft = {};
            this.setActiveSection("list");
            await this.fetchPolls();
            this.setSuccess(this.t("pollDeletedSuccess"));
          } catch (error) {
            this.setError(this.resolveError(error.payload, "Could not delete poll."));
          }
        });
      }
    };
  };
})();
