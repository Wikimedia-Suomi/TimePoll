(() => {
  const domains = window.TimePollAppDomains || (window.TimePollAppDomains = {});

  domains.createAuthProfileDomainMethods = function createAuthProfileDomainMethods({
    apiFetch,
    safeLocalStorageGetItem,
    safeLocalStorageSetItem,
    translations
  }) {
    return {
      async changeLanguage() {
        safeLocalStorageSetItem("timepoll-language", this.language);
        document.documentElement.lang = this.language;
        try {
          await apiFetch("/api/i18n/language/", {
            method: "POST",
            body: { language: this.language }
          });
        } catch (error) {
          this.setError(this.resolveError(error.payload, "Unable to switch language."));
        }
      },
      async fetchMyData() {
        if (!this.session.authenticated) {
          this.profileData = null;
          return;
        }
        await this.waitForPendingVoteSync();
        this.profileLoading = true;
        try {
          const data = await apiFetch("/api/auth/me/");
          this.profileData = data;
        } catch (error) {
          this.setError(this.resolveError(error.payload, "Could not load your data."));
        } finally {
          this.profileLoading = false;
        }
      },
      isProfileVoteDeleting(optionId) {
        return Boolean(this.profileVoteDeletingOptionIds[optionId]);
      },
      profileVoteDateRangeLabel(vote) {
        if (!vote || typeof vote !== "object") {
          return "";
        }
        const startLabel = this.formatDate(vote.option_starts_at);
        const endLabel = vote.option_ends_at ? this.formatDate(vote.option_ends_at) : "";
        if (startLabel && endLabel) {
          return `${startLabel} - ${endLabel}`;
        }
        return startLabel || endLabel || "";
      },
      async refreshSelectedPollIfMatches(pollId) {
        if (!this.selectedPoll) {
          return;
        }
        if (String(this.selectedPoll.id) !== String(pollId)) {
          return;
        }
        try {
          const data = await apiFetch(`/api/polls/${encodeURIComponent(String(pollId))}/`);
          this.resetVoteSyncState();
          this.selectedPoll = data.poll;
          this.applyVoteDraft();
        } catch (_error) {
          // ignore refresh failure on profile page
        }
      },
      async deleteSingleVoteFromProfile(vote) {
        if (!vote || typeof vote !== "object") {
          return;
        }
        const pollId = String(vote.poll_id || "").trim();
        const optionId = Number(vote.poll_option_id);
        if (!pollId || !Number.isInteger(optionId)) {
          return;
        }
        if (this.profileDeleting || this.profileLoading || this.isProfileVoteDeleting(optionId)) {
          return;
        }

        this.clearFeedback();
        this.profileDeleteSummary = null;
        this.profileVoteDeletingOptionIds[optionId] = true;
        try {
          await apiFetch(`/api/polls/${encodeURIComponent(pollId)}/votes/${optionId}/`, {
            method: "DELETE"
          });
          await this.fetchMyData();
          await this.fetchPolls();
          await this.refreshSelectedPollIfMatches(pollId);
          this.setSuccess(this.t("voteDeleted"));
        } catch (error) {
          this.setError(this.resolveError(error.payload, "Could not delete vote."));
        } finally {
          delete this.profileVoteDeletingOptionIds[optionId];
        }
      },
      async openProfile() {
        if (!this.session.authenticated) {
          this.openAuthDialog();
          return;
        }
        this.rememberProfileSectionReturn();
        this.setActiveSection("profile", { forceFocus: true });
        await this.fetchMyData();
      },
      downloadMyDataJson() {
        if (!this.profileData) {
          return;
        }
        const safeName = this.session.identity && this.session.identity.name
          ? String(this.session.identity.name).replace(/[^a-zA-Z0-9_-]+/g, "_")
          : "user";
        const blob = new Blob([JSON.stringify(this.profileData, null, 2)], { type: "application/json" });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `timepoll-${safeName}-data.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      },
      async deleteOwnData() {
        if (!this.session.authenticated) {
          this.openAuthDialog();
          return;
        }
        if (!window.confirm(this.t("profileDeleteConfirm"))) {
          return;
        }

        this.clearFeedback();
        this.profileDeleting = true;
        this.profileVoteDeletingOptionIds = {};
        try {
          const result = await apiFetch("/api/auth/me/", { method: "DELETE" });
          this.profileDeleteSummary = result;
          this.isEditingPoll = false;
          this.editForm = null;
          this.resetVoteSyncState();
          this.selectedPoll = null;
          this.voteDraft = {};
          await this.fetchPolls();

          if (result.deleted_identity) {
            this.session.authenticated = false;
            this.session.identity = null;
            this.profileData = null;
            this.setActiveSection("list");
            this.setSuccess(this.t("profileDeleteDoneAccountRemoved"));
            return;
          }

          await this.fetchMyData();
          this.setSuccess(this.t("profileDeleteDone"));
        } catch (error) {
          this.setError(this.resolveError(error.payload, "Could not delete your data."));
        } finally {
          this.profileDeleting = false;
        }
      },
      openAuthDialog() {
        this._authDialogReturnFocus = document.activeElement instanceof HTMLElement
          ? document.activeElement
          : null;
        this.showAuthDialog = true;
        this.authForm.name = this.authForm.name || "";
        this.authForm.pin = "";
        this.focusAuthDialogInitialField();
      },
      async submitAuth() {
        this.clearFeedback();
        try {
          const data = await apiFetch("/api/auth/login/", {
            method: "POST",
            body: {
              name: this.authForm.name,
              pin: this.authForm.pin
            }
          });

          const returnFocusTarget = this._authDialogReturnFocus;
          const hadPendingAction = Boolean(this.pendingAction);
          this.session.authenticated = data.authenticated;
          this.session.identity = data.identity;
          this.closeAuthDialog({ restoreFocus: false, clearPendingAction: false });
          this.authForm.pin = "";
          this.profileData = null;
          this.profileVoteDeletingOptionIds = {};
          this.profileDeleteSummary = null;
          this.setSuccess(data.created ? this.t("createdLoginSuccess") : this.t("loginSuccess"));

          await this.fetchPolls();
          if (this.activeSection === "selected" && this.selectedPoll) {
            await this.openPoll(this.selectedPoll.id, { preserveFeedback: true });
          }
          if (this.activeSection === "create" && !String(this.createForm && this.createForm.identifier || "").trim()) {
            await this.refreshCreateIdentifierSuggestion();
          }

          if (this.pendingAction) {
            const action = this.pendingAction;
            this.pendingAction = null;
            await action();
          }
          await this.$nextTick();
          this.focusAuthSuccessTarget(returnFocusTarget, { preferSectionTarget: hadPendingAction });
        } catch (error) {
          this.setError(this.resolveError(error.payload, this.t("authNeeded")));
        }
      },
      async logout() {
        this.clearFeedback();
        try {
          await apiFetch("/api/auth/logout/", { method: "POST" });
          this.session.authenticated = false;
          this.session.identity = null;
          this.resetVoteSyncState();
          this.voteDraft = {};
          this.profileData = null;
          this.profileVoteDeletingOptionIds = {};
          this.profileDeleteSummary = null;
          this.setSuccess(this.t("logoutSuccess"));
          await this.fetchPolls();
          if (this.activeSection === "selected" && this.selectedPoll) {
            await this.openPoll(this.selectedPoll.id, { preserveFeedback: true });
          }
        } catch (error) {
          this.setError(this.resolveError(error.payload, "Logout failed."));
        }
      },
      ensureAuthenticated(action) {
        if (this.session.authenticated) {
          return action();
        }
        this.pendingAction = action;
        this.openAuthDialog();
        return Promise.resolve();
      },
      async fetchSession() {
        try {
          const sessionData = await apiFetch("/api/auth/session/");
          this.session.authenticated = sessionData.authenticated;
          this.session.identity = sessionData.identity;

          const storedLanguage = safeLocalStorageGetItem("timepoll-language");
          if (storedLanguage && translations[storedLanguage]) {
            this.language = storedLanguage;
          } else if (sessionData.language && translations[sessionData.language]) {
            this.language = sessionData.language;
          }
        } catch (_error) {
          this.session.authenticated = false;
          this.session.identity = null;
        }
      }
    };
  };
})();
