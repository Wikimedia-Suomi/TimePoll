(() => {
  function showAppLogicLoadError() {
    const renderError = () => {
      const root = document.getElementById("app");
      if (root) {
        root.innerHTML = "<p class='feedback error'>TimePoll app logic failed to load.</p>";
      }
    };

    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", renderError, { once: true });
      return;
    }

    renderError();
  }

  const logic = window.TimePollLogic;
  if (!logic) {
    showAppLogicLoadError();
    return;
  }

  const {
    autoGrowScheduleForm,
    buildPollUrlState,
    calendarTimezonePreferenceStorageKeyForSession,
    collectDayOptionIdsFromRows,
    collectRowOptionIdsFromCells,
    extractPollIdFromSearch,
    filterRowsForVisibleDaysAndMinYesVotes,
    filterWeekRowsByMinYesVotes,
    filterTimezoneSuggestionOptions,
    isVoteStatusValue,
    loadCalendarTimezonePreferenceValue,
    matchesYesVoteFilter,
    nextVoteStatus,
    readOptionCount,
    serializeCalendarTimezonePreference,
    toggleWeekdaySelection
  } = logic;

  if (
    typeof autoGrowScheduleForm !== "function"
    || typeof buildPollUrlState !== "function"
    || typeof calendarTimezonePreferenceStorageKeyForSession !== "function"
    || typeof collectDayOptionIdsFromRows !== "function"
    || typeof collectRowOptionIdsFromCells !== "function"
    || typeof extractPollIdFromSearch !== "function"
    || typeof filterRowsForVisibleDaysAndMinYesVotes !== "function"
    || typeof filterWeekRowsByMinYesVotes !== "function"
    || typeof filterTimezoneSuggestionOptions !== "function"
    || typeof isVoteStatusValue !== "function"
    || typeof loadCalendarTimezonePreferenceValue !== "function"
    || typeof matchesYesVoteFilter !== "function"
    || typeof nextVoteStatus !== "function"
    || typeof readOptionCount !== "function"
    || typeof serializeCalendarTimezonePreference !== "function"
    || typeof toggleWeekdaySelection !== "function"
  ) {
    showAppLogicLoadError();
    return;
  }

  const successFeedbackAutoCloseMs = 3500;
  const voteSyncDebounceMs = 0;
  const csrfRefreshPath = "/api/auth/session/";
  let csrfRefreshPromise = null;

const translations = {
    en: {
      appTitle: "TimePoll",
      appSubtitle: "Vote on times to agree on schedules.",
      language: "Language",
      hello: "Hello,",
      login: "Login",
      logout: "Logout",
      createPoll: "Create new poll",
      sectionPollList: "Poll list",
      sectionCreatePoll: "Create poll dialog",
      sectionSelectedPoll: "Selected poll",
      workspaceSections: "Workspace sections",
      noSelectedPoll: "Select a poll from the list.",
      createHelp: "Select full start/end days. Time slots are generated automatically in 60-minute blocks.",
      pollIdentifier: "Poll identifier",
      pollIdentifierHelp:
        "Optional. Used in the poll link. Allowed characters: A-Z, a-z, 0-9 and underscore (_). Example: Poll_Name_2026",
      title: "Title",
      description: "Description",
      startDate: "Start date",
      endDate: "End date",
      timezone: "Timezone",
      calendarTimezone: "Calendar timezone",
      calendarTimezonePoll: "Poll creator selected timezone",
      calendarTimezoneBrowser: "Browser timezone",
      calendarTimezoneOwn: "Own timezone",
      voteDisplayMode: "Answer view",
      voteDisplayModeResults: "Result mode",
      voteDisplayModeOwn: "Own answers",
      minYesVotesFilter: "Show options with at least this many Yes votes",
      noRowsMatchFilter: "No options match the current Yes filter.",
      timezoneHelp: "Start typing to filter IANA timezones, for example Europe/Helsinki or UTC.",
      timezoneSelected: "Selected timezone",
      validationRequired: "{field} is required.",
      validationInvalid: "{field} is invalid.",
      validationTooLong: "{field} is too long.",
      validationFormInvalid: "Poll form is invalid.",
      validationInvalidValue: "Invalid value.",
      dailyStartHour: "Daily start hour",
      dailyEndHour: "Daily end hour",
      allowedWeekdays: "Allowed weekdays",
      weekdayMon: "Mon",
      weekdayTue: "Tue",
      weekdayWed: "Wed",
      weekdayThu: "Thu",
      weekdayFri: "Fri",
      weekdaySat: "Sat",
      weekdaySun: "Sun",
      timeOptions: "Time options",
      optionLabel: "Option label",
      startsAt: "Starts at",
      endsAt: "Ends at",
      removeOption: "Remove option",
      addOption: "Add option",
      polls: "Polls",
      participants: "participants",
      open: "open",
      closed: "closed",
      noPolls: "No polls yet.",
      noDescription: "No description",
      createdBy: "Created by",
      closePoll: "Close poll",
      reopenPoll: "Reopen poll",
      deletePoll: "Delete poll",
      editPoll: "Edit poll",
      editHelp: "You can edit poll settings. Time slots that already have votes cannot be removed.",
      editStartDateBoundByEndDate: "Start date cannot be later than the selected end date.",
      editStartDateBoundByVotes: "Existing votes require the start date to be on or before {date}.",
      editEndDateBoundByStartDate: "End date cannot be earlier than the selected start date.",
      editEndDateBoundByVotes: "Existing votes require the end date to be on or after {date}.",
      editStartHourBoundByEndHour: "Day start hour must be earlier than the selected end hour.",
      editStartHourBoundByVotes: "Existing votes require the day start hour to be at or before {hour}.",
      editEndHourBoundByStartHour: "Day end hour must be later than the selected start hour.",
      editEndHourBoundByVotes: "Existing votes require the day end hour to be at or after {hour}.",
      editAllowedWeekdaysBoundByVotes: "Existing votes require these weekdays to remain selected: {days}.",
      editTimezoneAutoGrowNotice: "Timezone change expanded the schedule so existing votes remain valid.",
      editTimezoneConfirmTitle: "Confirm timezone change",
      editTimezoneConfirmDescription:
        "Changing timezone from {from} to {to} expands the schedule so existing votes remain valid.",
      editTimezoneConfirmPrompt: "Please confirm these automatic changes before applying them.",
      editTimezoneConfirmButton: "Apply timezone change",
      saveChanges: "Save changes",
      cancelEdit: "Cancel edit",
      cancel: "Cancel",
      pollOpen: "Poll is open",
      pollClosed: "Poll is closed",
      availabilityTable: "Availability table",
      weekOf: "Week of",
      timeColumn: "Time",
      daysRange: "Days",
      prevDays: "Previous days",
      nextDays: "Next days",
      timeOption: "Time option",
      noSlots: "No selectable slots in this poll.",
      yesVotes: "Yes votes",
      noVotes: "No votes",
      maybeVotes: "Maybe votes",
      myVote: "My vote",
      actions: "Actions",
      voteYes: "Yes",
      voteNo: "No",
      voteMaybe: "Maybe",
      noVote: "No vote",
      voteCellKeyboardHelp: "Use arrow keys to move between time options. Press Enter or Space to open vote choices, then choose with arrow keys and confirm with Enter or Space.",
      voteSavedStatus: "Vote saved: {status}.",
      voteCleared: "Vote cleared.",
      votesSaved: "Votes saved.",
      deleteVote: "Delete vote",
      authNeeded: "Enter your name and PIN to continue. A new user is created automatically if needed.",
      authPrompt: "Use your name and PIN. If the name does not exist yet, a new user is created automatically.",
      name: "Name",
      pin: "PIN code",
      createdSuccess: "Poll created successfully.",
      pollUpdatedSuccess: "Poll updated successfully.",
      voteDeleted: "Vote deleted.",
      pollClosedSuccess: "Poll closed.",
      pollReopenedSuccess: "Poll reopened.",
      pollDeletedSuccess: "Poll deleted.",
      loginSuccess: "Logged in.",
      createdLoginSuccess: "New user created and logged in.",
      logoutSuccess: "Logged out.",
      backToPollList: "Back to poll list",
      backToProfile: "Back to my data",
      backToSelectedPoll: "Back to poll",
      backToCreatePoll: "Back to create poll",
      discardCreateConfirm: "Discard this draft and return to the poll list?",
      confirmDeletePoll: "Delete this poll permanently?",
      dismissFeedback: "Dismiss notification",
      profileTitle: "My data",
      profileRefresh: "Refresh",
      profileLoading: "Loading your data...",
      profileEmpty: "No data loaded yet.",
      profileDownloadJson: "Download JSON",
      profileDeleteOwnData: "Delete own data",
      profileDeleteConfirm:
        "Delete your votes and deletable polls now? Polls with other users' votes will remain.",
      profileDeleteDone: "Own data deleted where possible.",
      profileDeleteDoneAccountRemoved: "All personal data removed. Your account was deleted.",
      profileDeletedVotes: "Deleted votes",
      profileDeletedPolls: "Deleted polls",
      profileRemainingPolls: "Remaining created polls",
      profileRemainingPollsWithOthers: "Remaining polls with other users' votes",
      profileIdentity: "User details",
      profileStats: "Statistics",
      profileCreatedAt: "Created at",
      profileUpdatedAt: "Updated at",
      profileCreatedPolls: "Created polls",
      profileNoCreatedPolls: "No created polls.",
      profileVotes: "My votes",
      profileNoVotes: "No votes.",
      profileVoteTime: "Time",
      profileOpenPoll: "Open poll",
      profileVoteCount: "Vote count",
      profileDistinctVotedPollCount: "Polls voted in"
    },
    fi: {
      appTitle: "TimePoll",
      appSubtitle: "Äänestä ajoista sopiaksesi aikataulut",
      language: "Kieli",
      hello: "Hei,",
      login: "Kirjaudu",
      logout: "Kirjaudu ulos",
      createPoll: "Luo uusi kysely",
      sectionPollList: "Kyselylista",
      sectionCreatePoll: "Luo kysely dialogi",
      sectionSelectedPoll: "Valittu kysely",
      workspaceSections: "Työtilan osiot",
      noSelectedPoll: "Valitse kysely listasta.",
      createHelp: "Valitse alku- ja loppupäivät. Aikavaihtoehdot luodaan automaattisesti 60 minuutin jaksoina.",
      pollIdentifier: "Kyselyn tunniste",
      pollIdentifierHelp:
        "Valinnainen. Tunnistetta käytetään kyselyyn viittaavassa linkissä. Sallitut merkit: A-Z, a-z, 0-9 ja alaviiva (_). Esimerkki: Poll_Name_2026",
      title: "Otsikko",
      description: "Kuvaus",
      startDate: "Alkupäivä",
      endDate: "Loppupäivä",
      timezone: "Aikavyöhyke",
      calendarTimezone: "Kalenterin aikavyöhyke",
      calendarTimezonePoll: "Kyselyn luojan valitsema aikavyöhyke",
      calendarTimezoneBrowser: "Selaimen aikavyöhyke",
      calendarTimezoneOwn: "Oma aikavyöhyke",
      voteDisplayMode: "Vastausnäkymä",
      voteDisplayModeResults: "Tulostila",
      voteDisplayModeOwn: "Omat vastaukset",
      minYesVotesFilter: "Näytä valinnat, joissa vähintään näin monta Kyllä-ääntä",
      noRowsMatchFilter: "Yksikään valinta ei täytä nykyistä Kyllä-suodatinta.",
      timezoneHelp: "Ala kirjoittaa suodattaaksesi IANA-aikavyöhykkeitä, esimerkiksi Europe/Helsinki tai UTC.",
      timezoneSelected: "Valittu aikavyöhyke",
      validationRequired: "{field} on pakollinen.",
      validationInvalid: "{field} on virheellinen.",
      validationTooLong: "{field} on liian pitkä.",
      validationFormInvalid: "Kyselyn lomaketiedot ovat virheelliset.",
      validationInvalidValue: "Virheellinen arvo.",
      dailyStartHour: "Päivän aloitustunti",
      dailyEndHour: "Päivän lopetustunti",
      allowedWeekdays: "Sallitut viikonpäivät",
      weekdayMon: "Ma",
      weekdayTue: "Ti",
      weekdayWed: "Ke",
      weekdayThu: "To",
      weekdayFri: "Pe",
      weekdaySat: "La",
      weekdaySun: "Su",
      timeOptions: "Aikavaihtoehdot",
      optionLabel: "Vaihtoehdon nimi",
      startsAt: "Alkaa",
      endsAt: "Päättyy",
      removeOption: "Poista vaihtoehto",
      addOption: "Lisää vaihtoehto",
      polls: "Kyselyt",
      participants: "osallistujaa",
      open: "auki",
      closed: "suljettu",
      noPolls: "Ei kyselyitä vielä.",
      noDescription: "Ei kuvausta",
      createdBy: "Luoja",
      closePoll: "Sulje kysely",
      reopenPoll: "Avaa kysely",
      deletePoll: "Poista kysely",
      editPoll: "Muokkaa kyselyä",
      editHelp: "Voit muokata kyselyn tietoja. Ääniä saaneita aikaslotteja ei voi poistaa.",
      editStartDateBoundByEndDate: "Alkupäivä ei voi olla valittua loppupäivää myöhemmin.",
      editStartDateBoundByVotes: "Annetut vastaukset edellyttävät, että alkupäivä on viimeistään {date}.",
      editEndDateBoundByStartDate: "Loppupäivä ei voi olla valittua alkupäivää aikaisemmin.",
      editEndDateBoundByVotes: "Annetut vastaukset edellyttävät, että loppupäivä on aikaisintaan {date}.",
      editStartHourBoundByEndHour: "Päivän aloitustunnin on oltava ennen valittua lopetustuntia.",
      editStartHourBoundByVotes: "Annetut vastaukset edellyttävät, että päivän aloitustunti on viimeistään {hour}.",
      editEndHourBoundByStartHour: "Päivän lopetustunnin on oltava valittua aloitustuntia myöhemmin.",
      editEndHourBoundByVotes: "Annetut vastaukset edellyttävät, että päivän lopetustunti on aikaisintaan {hour}.",
      editAllowedWeekdaysBoundByVotes: "Annetut vastaukset edellyttävät, että nämä viikonpäivät pysyvät valittuina: {days}.",
      editTimezoneAutoGrowNotice: "Aikavyöhykkeen vaihto laajensi aikataulua, jotta annetut vastaukset säilyvät voimassa.",
      editTimezoneConfirmTitle: "Vahvista aikavyöhykkeen vaihto",
      editTimezoneConfirmDescription:
        "Aikavyöhykkeen vaihto {from} -> {to} laajentaa aikataulua, jotta annetut vastaukset säilyvät voimassa.",
      editTimezoneConfirmPrompt: "Vahvista nämä automaattiset muutokset ennen käyttöönottoa.",
      editTimezoneConfirmButton: "Vahvista aikavyöhykkeen vaihto",
      saveChanges: "Tallenna muutokset",
      cancelEdit: "Peru muokkaus",
      cancel: "Peru",
      pollOpen: "Kysely on auki",
      pollClosed: "Kysely on suljettu",
      availabilityTable: "Saatavuustaulukko",
      weekOf: "Viikko alkaen",
      timeColumn: "Aika",
      daysRange: "Päivät",
      prevDays: "Edelliset päivät",
      nextDays: "Seuraavat päivät",
      timeOption: "Aikavaihtoehto",
      noSlots: "Tässä kyselyssä ei ole valittavia slotteja.",
      yesVotes: "Kyllä-äänet",
      noVotes: "Ei-äänet",
      maybeVotes: "Ehkä-äänet",
      myVote: "Oma ääni",
      actions: "Toiminnot",
      voteYes: "Kyllä",
      voteNo: "Ei",
      voteMaybe: "Ehkä",
      noVote: "Ei ääntä",
      voteCellKeyboardHelp: "Liiku aikavaihtoehtojen välillä nuolinäppäimillä. Avaa äänivalinnat Enterillä tai välilyönnillä, valitse nuolilla ja vahvista Enterillä tai välilyönnillä.",
      voteSavedStatus: "Ääni tallennettu: {status}.",
      voteCleared: "Ääni poistettu.",
      votesSaved: "Äänet tallennettu.",
      deleteVote: "Poista ääni",
      authNeeded: "Syötä nimi ja PIN-koodi jatkaaksesi. Uusi käyttäjä luodaan automaattisesti tarvittaessa.",
      authPrompt: "Käytä nimeä ja PIN-koodia. Jos nimeä ei ole vielä olemassa, uusi käyttäjä luodaan automaattisesti.",
      name: "Nimi",
      pin: "PIN-koodi",
      createdSuccess: "Kysely luotu.",
      pollUpdatedSuccess: "Kysely päivitetty.",
      voteDeleted: "Ääni poistettu.",
      pollClosedSuccess: "Kysely suljettu.",
      pollReopenedSuccess: "Kysely avattu uudelleen.",
      pollDeletedSuccess: "Kysely poistettu.",
      loginSuccess: "Kirjautuminen onnistui.",
      createdLoginSuccess: "Uusi käyttäjä luotiin ja kirjautuminen onnistui.",
      logoutSuccess: "Uloskirjautuminen onnistui.",
      backToPollList: "Takaisin kyselylistaan",
      backToProfile: "Takaisin omiin tietoihin",
      backToSelectedPoll: "Takaisin kyselyyn",
      backToCreatePoll: "Takaisin kyselyn luontiin",
      discardCreateConfirm: "Hylätäänkö luonnos ja palataan kyselylistaan?",
      confirmDeletePoll: "Poistetaanko kysely pysyvästi?",
      dismissFeedback: "Sulje ilmoitus",
      profileTitle: "Omat tiedot",
      profileRefresh: "Päivitä",
      profileLoading: "Ladataan tietojasi...",
      profileEmpty: "Tietoja ei ole vielä ladattu.",
      profileDownloadJson: "Lataa JSON",
      profileDeleteOwnData: "Poista omat tiedot",
      profileDeleteConfirm:
        "Poistetaanko äänesi ja poistettavissa olevat kyselyt nyt? Kyselyt, joissa on muiden ääniä, jäävät jäljelle.",
      profileDeleteDone: "Omat tiedot poistettu siltä osin kuin mahdollista.",
      profileDeleteDoneAccountRemoved: "Kaikki henkilötiedot poistettiin. Käyttäjätili poistettiin.",
      profileDeletedVotes: "Poistetut äänet",
      profileDeletedPolls: "Poistetut kyselyt",
      profileRemainingPolls: "Jäljellä olevat luodut kyselyt",
      profileRemainingPollsWithOthers: "Jäljellä olevat kyselyt, joissa on muiden ääniä",
      profileIdentity: "Käyttäjätiedot",
      profileStats: "Tilastot",
      profileCreatedAt: "Luotu",
      profileUpdatedAt: "Päivitetty",
      profileCreatedPolls: "Luodut kyselyt",
      profileNoCreatedPolls: "Ei luotuja kyselyitä.",
      profileVotes: "Omat äänet",
      profileNoVotes: "Ei ääniä.",
      profileVoteTime: "Aika",
      profileOpenPoll: "Avaa kysely",
      profileVoteCount: "Äänten määrä",
      profileDistinctVotedPollCount: "Äänestetyt kyselyt"
    },
    sv: {
      appTitle: "TimePoll",
      appSubtitle: "Rösta på tider för att komma överens om scheman.",
      language: "Språk",
      hello: "Hej,",
      login: "Logga in",
      logout: "Logga ut",
      createPoll: "Skapa ny omröstning",
      sectionPollList: "Omröstningslista",
      sectionCreatePoll: "Skapa omröstningsdialog",
      sectionSelectedPoll: "Vald omröstning",
      workspaceSections: "Arbetsytans sektioner",
      noSelectedPoll: "Välj en omröstning från listan.",
      createHelp: "Välj hela start- och slutdagar. Tidsalternativ skapas automatiskt i 60-minutersblock.",
      pollIdentifier: "Omröstningsidentifierare",
      pollIdentifierHelp:
        "Valfritt. Identifieraren används i länken till omröstningen. Tillåtna tecken: A-Z, a-z, 0-9 och understreck (_). Exempel: Poll_Name_2026",
      title: "Titel",
      description: "Beskrivning",
      startDate: "Startdatum",
      endDate: "Slutdatum",
      timezone: "Tidszon",
      calendarTimezone: "Kalenderns tidszon",
      calendarTimezonePoll: "Skaparens valda tidszon",
      calendarTimezoneBrowser: "Webbläsarens tidszon",
      calendarTimezoneOwn: "Egen tidszon",
      voteDisplayMode: "Svarsvy",
      voteDisplayModeResults: "Resultatläge",
      voteDisplayModeOwn: "Egna svar",
      minYesVotesFilter: "Visa alternativ med minst så här många Ja-röster",
      noRowsMatchFilter: "Inga alternativ matchar det aktuella Ja-filtret.",
      timezoneHelp: "Börja skriva för att filtrera IANA-tidszoner, till exempel Europe/Helsinki eller UTC.",
      timezoneSelected: "Vald tidszon",
      validationRequired: "{field} är obligatoriskt.",
      validationInvalid: "{field} är ogiltigt.",
      validationTooLong: "{field} är för långt.",
      validationFormInvalid: "Omröstningsformuläret är ogiltigt.",
      validationInvalidValue: "Ogiltigt värde.",
      dailyStartHour: "Daglig starttimme",
      dailyEndHour: "Daglig sluttimme",
      allowedWeekdays: "Tillåtna veckodagar",
      weekdayMon: "Mån",
      weekdayTue: "Tis",
      weekdayWed: "Ons",
      weekdayThu: "Tor",
      weekdayFri: "Fre",
      weekdaySat: "Lör",
      weekdaySun: "Sön",
      timeOptions: "Tidsalternativ",
      optionLabel: "Alternativnamn",
      startsAt: "Startar",
      endsAt: "Slutar",
      removeOption: "Ta bort alternativ",
      addOption: "Lägg till alternativ",
      polls: "Omröstningar",
      participants: "deltagare",
      open: "öppen",
      closed: "stängd",
      noPolls: "Inga omröstningar ännu.",
      noDescription: "Ingen beskrivning",
      createdBy: "Skapad av",
      closePoll: "Stäng omröstning",
      reopenPoll: "Öppna omröstning igen",
      deletePoll: "Ta bort omröstning",
      editPoll: "Redigera omröstning",
      editHelp: "Du kan redigera omröstningens inställningar. Tidslots med röster kan inte tas bort.",
      editTimezoneAutoGrowNotice: "Byte av tidszon utökade schemat så att befintliga röster fortfarande är giltiga.",
      editTimezoneConfirmTitle: "Bekräfta byte av tidszon",
      editTimezoneConfirmDescription:
        "Att byta tidszon från {from} till {to} utökar schemat så att befintliga röster fortsätter att vara giltiga.",
      editTimezoneConfirmPrompt: "Bekräfta dessa automatiska ändringar innan de används.",
      editTimezoneConfirmButton: "Bekräfta byte av tidszon",
      saveChanges: "Spara ändringar",
      cancelEdit: "Avbryt redigering",
      cancel: "Avbryt",
      pollOpen: "Omröstningen är öppen",
      pollClosed: "Omröstningen är stängd",
      availabilityTable: "Tillgänglighetstabell",
      weekOf: "Vecka från",
      timeColumn: "Tid",
      daysRange: "Dagar",
      prevDays: "Föregående dagar",
      nextDays: "Nästa dagar",
      timeOption: "Tidsalternativ",
      noSlots: "Inga valbara slots i denna omröstning.",
      yesVotes: "Ja-röster",
      noVotes: "Nej-röster",
      maybeVotes: "Kanske-röster",
      myVote: "Min röst",
      actions: "Åtgärder",
      voteYes: "Ja",
      voteNo: "Nej",
      voteMaybe: "Kanske",
      noVote: "Ingen röst",
      voteCellKeyboardHelp: "Flytta mellan tidsalternativen med piltangenterna. Öppna röstval med Enter eller mellanslag, välj med pilarna och bekräfta med Enter eller mellanslag.",
      voteSavedStatus: "Röst sparad: {status}.",
      voteCleared: "Röst borttagen.",
      votesSaved: "Röster sparade.",
      deleteVote: "Ta bort röst",
      authNeeded: "Ange namn och PIN-kod för att fortsätta. En ny användare skapas automatiskt vid behov.",
      authPrompt: "Använd namn och PIN-kod. Om namnet inte finns skapas en ny användare automatiskt.",
      name: "Namn",
      pin: "PIN-kod",
      createdSuccess: "Omröstning skapad.",
      pollUpdatedSuccess: "Omröstning uppdaterad.",
      voteDeleted: "Röst borttagen.",
      pollClosedSuccess: "Omröstning stängd.",
      pollReopenedSuccess: "Omröstning öppnad igen.",
      pollDeletedSuccess: "Omröstning borttagen.",
      loginSuccess: "Inloggad.",
      createdLoginSuccess: "Ny användare skapad och inloggad.",
      logoutSuccess: "Utloggad.",
      backToPollList: "Tillbaka till omröstningslistan",
      backToProfile: "Tillbaka till mina uppgifter",
      backToSelectedPoll: "Tillbaka till omröstningen",
      backToCreatePoll: "Tillbaka till att skapa omröstning",
      discardCreateConfirm: "Kassera utkastet och återgå till omröstningslistan?",
      confirmDeletePoll: "Ta bort denna omröstning permanent?",
      dismissFeedback: "Stäng meddelande",
      profileTitle: "Mina uppgifter",
      profileRefresh: "Uppdatera",
      profileLoading: "Laddar dina uppgifter...",
      profileEmpty: "Inga uppgifter laddade ännu.",
      profileDownloadJson: "Ladda ner JSON",
      profileDeleteOwnData: "Radera egna uppgifter",
      profileDeleteConfirm:
        "Radera dina röster och omröstningar som kan tas bort nu? Omröstningar med andras röster blir kvar.",
      profileDeleteDone: "Egna uppgifter raderades där det var möjligt.",
      profileDeleteDoneAccountRemoved: "Alla personuppgifter raderades. Ditt konto togs bort.",
      profileDeletedVotes: "Raderade röster",
      profileDeletedPolls: "Raderade omröstningar",
      profileRemainingPolls: "Kvarvarande skapade omröstningar",
      profileRemainingPollsWithOthers: "Kvarvarande omröstningar med andras röster",
      profileIdentity: "Användaruppgifter",
      profileStats: "Statistik",
      profileCreatedAt: "Skapad",
      profileUpdatedAt: "Uppdaterad",
      profileCreatedPolls: "Skapade omröstningar",
      profileNoCreatedPolls: "Inga skapade omröstningar.",
      profileVotes: "Mina röster",
      profileNoVotes: "Inga röster.",
      profileVoteTime: "Tid",
      profileOpenPoll: "Öppna omröstning",
      profileVoteCount: "Antal röster",
      profileDistinctVotedPollCount: "Omröstningar du har röstat i"
    },
    no: {
      appTitle: "TimePoll",
      appSubtitle: "Stem på tider for å avtale timeplaner.",
      language: "Språk",
      hello: "Hei,",
      login: "Logg inn",
      logout: "Logg ut",
      createPoll: "Opprett ny avstemning",
      sectionPollList: "Avstemningsliste",
      sectionCreatePoll: "Opprett avstemningsdialog",
      sectionSelectedPoll: "Valgt avstemning",
      workspaceSections: "Arbeidsområdeseksjoner",
      noSelectedPoll: "Velg en avstemning fra listen.",
      createHelp: "Velg hele start- og sluttdager. Tidsalternativer opprettes automatisk i 60-minuttersblokker.",
      pollIdentifier: "Avstemningsidentifikator",
      pollIdentifierHelp:
        "Valgfritt. Identifikatoren brukes i lenken til avstemningen. Tillatte tegn: A-Z, a-z, 0-9 og understrek (_). Eksempel: Poll_Name_2026",
      title: "Tittel",
      description: "Beskrivelse",
      startDate: "Startdato",
      endDate: "Sluttdato",
      timezone: "Tidssone",
      calendarTimezone: "Kalendertidssone",
      calendarTimezonePoll: "Avstemningsoppretterens valgte tidssone",
      calendarTimezoneBrowser: "Nettleserens tidssone",
      calendarTimezoneOwn: "Egen tidssone",
      voteDisplayMode: "Svarvisning",
      voteDisplayModeResults: "Resultatmodus",
      voteDisplayModeOwn: "Egne svar",
      minYesVotesFilter: "Vis alternativer med minst så mange Ja-stemmer",
      noRowsMatchFilter: "Ingen alternativer samsvarer med gjeldende Ja-filter.",
      timezoneHelp: "Begynn å skrive for å filtrere IANA-tidssoner, for eksempel Europe/Helsinki eller UTC.",
      timezoneSelected: "Valgt tidssone",
      validationRequired: "{field} er obligatorisk.",
      validationInvalid: "{field} er ugyldig.",
      validationTooLong: "{field} er for lang.",
      validationFormInvalid: "Skjemaet for avstemningen er ugyldig.",
      validationInvalidValue: "Ugyldig verdi.",
      dailyStartHour: "Daglig starttime",
      dailyEndHour: "Daglig sluttime",
      allowedWeekdays: "Tillatte ukedager",
      weekdayMon: "Man",
      weekdayTue: "Tir",
      weekdayWed: "Ons",
      weekdayThu: "Tor",
      weekdayFri: "Fre",
      weekdaySat: "Lør",
      weekdaySun: "Søn",
      timeOptions: "Tidsalternativer",
      optionLabel: "Alternativnavn",
      startsAt: "Starter",
      endsAt: "Slutter",
      removeOption: "Fjern alternativ",
      addOption: "Legg til alternativ",
      polls: "Avstemninger",
      participants: "deltakere",
      open: "åpen",
      closed: "lukket",
      noPolls: "Ingen avstemninger ennå.",
      noDescription: "Ingen beskrivelse",
      createdBy: "Opprettet av",
      closePoll: "Lukk avstemning",
      reopenPoll: "Åpne avstemning igjen",
      deletePoll: "Slett avstemning",
      editPoll: "Rediger avstemning",
      editHelp: "Du kan redigere avstemningsinnstillingene. Tidsluker som allerede har stemmer kan ikke fjernes.",
      editTimezoneAutoGrowNotice: "Bytte av tidssone utvidet planen slik at eksisterende stemmer fortsatt er gyldige.",
      editTimezoneConfirmTitle: "Bekreft bytte av tidssone",
      editTimezoneConfirmDescription:
        "Å bytte tidssone fra {from} til {to} utvider planen slik at eksisterende stemmer fortsatt er gyldige.",
      editTimezoneConfirmPrompt: "Bekreft disse automatiske endringene før de tas i bruk.",
      editTimezoneConfirmButton: "Bekreft bytte av tidssone",
      saveChanges: "Lagre endringer",
      cancelEdit: "Avbryt redigering",
      cancel: "Avbryt",
      pollOpen: "Avstemningen er åpen",
      pollClosed: "Avstemningen er lukket",
      availabilityTable: "Tilgjengelighetstabell",
      weekOf: "Uke fra",
      timeColumn: "Tid",
      daysRange: "Dager",
      prevDays: "Forrige dager",
      nextDays: "Neste dager",
      timeOption: "Tidsalternativ",
      noSlots: "Ingen valgbare tidsluker i denne avstemningen.",
      yesVotes: "Ja-stemmer",
      noVotes: "Nei-stemmer",
      maybeVotes: "Kanskje-stemmer",
      myVote: "Min stemme",
      actions: "Handlinger",
      voteYes: "Ja",
      voteNo: "Nei",
      voteMaybe: "Kanskje",
      noVote: "Ingen stemme",
      voteCellKeyboardHelp: "Flytt mellom tidsalternativene med piltastene. Åpne stemmevalgene med Enter eller mellomrom, velg med piltastene og bekreft med Enter eller mellomrom.",
      voteSavedStatus: "Stemme lagret: {status}.",
      voteCleared: "Stemme fjernet.",
      votesSaved: "Stemmer lagret.",
      deleteVote: "Slett stemme",
      authNeeded: "Skriv inn navn og PIN-kode for å fortsette. En ny bruker opprettes automatisk ved behov.",
      authPrompt: "Bruk navn og PIN-kode. Hvis navnet ikke finnes ennå, opprettes en ny bruker automatisk.",
      name: "Navn",
      pin: "PIN-kode",
      createdSuccess: "Avstemning opprettet.",
      pollUpdatedSuccess: "Avstemning oppdatert.",
      voteDeleted: "Stemme slettet.",
      pollClosedSuccess: "Avstemning lukket.",
      pollReopenedSuccess: "Avstemning åpnet på nytt.",
      pollDeletedSuccess: "Avstemning slettet.",
      loginSuccess: "Innlogget.",
      createdLoginSuccess: "Ny bruker opprettet og innlogget.",
      logoutSuccess: "Utlogget.",
      backToPollList: "Tilbake til avstemningslisten",
      backToProfile: "Tilbake til mine data",
      backToSelectedPoll: "Tilbake til avstemningen",
      backToCreatePoll: "Tilbake til opprett av avstemning",
      discardCreateConfirm: "Forkaste utkastet og gå tilbake til avstemningslisten?",
      confirmDeletePoll: "Slette denne avstemningen permanent?",
      dismissFeedback: "Lukk varsel",
      profileTitle: "Mine data",
      profileRefresh: "Oppdater",
      profileLoading: "Laster inn dataene dine...",
      profileEmpty: "Ingen data lastet inn ennå.",
      profileDownloadJson: "Last ned JSON",
      profileDeleteOwnData: "Slett egne data",
      profileDeleteConfirm:
        "Slette stemmene dine og avstemninger som kan slettes nå? Avstemninger med andres stemmer blir værende.",
      profileDeleteDone: "Egne data ble slettet der det var mulig.",
      profileDeleteDoneAccountRemoved: "Alle personopplysninger ble fjernet. Kontoen din ble slettet.",
      profileDeletedVotes: "Slettede stemmer",
      profileDeletedPolls: "Slettede avstemninger",
      profileRemainingPolls: "Gjenstående opprettede avstemninger",
      profileRemainingPollsWithOthers: "Gjenstående avstemninger med andres stemmer",
      profileIdentity: "Brukeropplysninger",
      profileStats: "Statistikk",
      profileCreatedAt: "Opprettet",
      profileUpdatedAt: "Oppdatert",
      profileCreatedPolls: "Opprettede avstemninger",
      profileNoCreatedPolls: "Ingen opprettede avstemninger.",
      profileVotes: "Mine stemmer",
      profileNoVotes: "Ingen stemmer.",
      profileVoteTime: "Tid",
      profileOpenPoll: "Åpne avstemning",
      profileVoteCount: "Antall stemmer",
      profileDistinctVotedPollCount: "Avstemninger du har stemt i"
    },
    et: {
      appTitle: "TimePoll",
      appSubtitle: "Hääleta aegade üle, et ajakavad kokku leppida.",
      language: "Keel",
      hello: "Tere,",
      login: "Logi sisse",
      logout: "Logi välja",
      createPoll: "Loo uus küsitlus",
      sectionPollList: "Küsitluste loend",
      sectionCreatePoll: "Küsitluse loomise dialoog",
      sectionSelectedPoll: "Valitud küsitlus",
      workspaceSections: "Tööala osad",
      noSelectedPoll: "Vali loendist küsitlus.",
      createHelp: "Vali täis algus- ja lõpppäevad. Ajavalikud luuakse automaatselt 60-minutiliste plokkidena.",
      pollIdentifier: "Küsitluse tunnus",
      pollIdentifierHelp:
        "Valikuline. Tunnust kasutatakse küsitlusele viitavas lingis. Lubatud märgid: A-Z, a-z, 0-9 ja alakriips (_). Näide: Poll_Name_2026",
      title: "Pealkiri",
      description: "Kirjeldus",
      startDate: "Alguskuupäev",
      endDate: "Lõppkuupäev",
      timezone: "Ajavöönd",
      calendarTimezone: "Kalendri ajavöönd",
      calendarTimezonePoll: "Küsitluse looja valitud ajavöönd",
      calendarTimezoneBrowser: "Brauseri ajavöönd",
      calendarTimezoneOwn: "Oma ajavöönd",
      voteDisplayMode: "Vastuste vaade",
      voteDisplayModeResults: "Tulemuste vaade",
      voteDisplayModeOwn: "Minu vastused",
      minYesVotesFilter: "Näita valikuid, kus on vähemalt nii palju Jah-hääli",
      noRowsMatchFilter: "Ükski valik ei vasta praegusele Jah-filtrile.",
      timezoneHelp: "IANA ajavööndite filtreerimiseks hakka kirjutama, näiteks Europe/Helsinki või UTC.",
      timezoneSelected: "Valitud ajavöönd",
      validationRequired: "{field} on kohustuslik.",
      validationInvalid: "{field} on vigane.",
      validationTooLong: "{field} on liiga pikk.",
      validationFormInvalid: "Küsitluse vormi andmed on vigased.",
      validationInvalidValue: "Vigane väärtus.",
      dailyStartHour: "Päeva algustund",
      dailyEndHour: "Päeva lõputund",
      allowedWeekdays: "Lubatud nädalapäevad",
      weekdayMon: "E",
      weekdayTue: "T",
      weekdayWed: "K",
      weekdayThu: "N",
      weekdayFri: "R",
      weekdaySat: "L",
      weekdaySun: "P",
      timeOptions: "Ajavalikud",
      optionLabel: "Valiku nimi",
      startsAt: "Algab",
      endsAt: "Lõpeb",
      removeOption: "Eemalda valik",
      addOption: "Lisa valik",
      polls: "Küsitlused",
      participants: "osalejat",
      open: "avatud",
      closed: "suletud",
      noPolls: "Küsitlusi pole veel.",
      noDescription: "Kirjeldus puudub",
      createdBy: "Looja",
      closePoll: "Sulge küsitlus",
      reopenPoll: "Ava küsitlus uuesti",
      deletePoll: "Kustuta küsitlus",
      editPoll: "Muuda küsitlust",
      editHelp: "Saad küsitluse seadeid muuta. Ajapesasid, millel on hääled, ei saa eemaldada.",
      editTimezoneAutoGrowNotice: "Ajavööndi vahetus laiendas ajakava, et olemasolevad hääled jääksid kehtima.",
      editTimezoneConfirmTitle: "Kinnita ajavööndi vahetus",
      editTimezoneConfirmDescription:
        "Ajavööndi vahetus {from} -> {to} laiendab ajakava, et olemasolevad hääled jääksid kehtima.",
      editTimezoneConfirmPrompt: "Kinnita need automaatsed muudatused enne rakendamist.",
      editTimezoneConfirmButton: "Kinnita ajavööndi vahetus",
      saveChanges: "Salvesta muudatused",
      cancelEdit: "Tühista muutmine",
      cancel: "Tühista",
      pollOpen: "Küsitlus on avatud",
      pollClosed: "Küsitlus on suletud",
      availabilityTable: "Saadavuse tabel",
      weekOf: "Nädal alates",
      timeColumn: "Aeg",
      daysRange: "Päevad",
      prevDays: "Eelmised päevad",
      nextDays: "Järgmised päevad",
      timeOption: "Ajavalik",
      noSlots: "Selles küsitluses pole valitavaid ajapesi.",
      yesVotes: "Jah-hääled",
      noVotes: "Ei-hääled",
      maybeVotes: "Võib-olla hääled",
      myVote: "Minu hääl",
      actions: "Toimingud",
      voteYes: "Jah",
      voteNo: "Ei",
      voteMaybe: "Võib-olla",
      noVote: "Hääl puudub",
      voteCellKeyboardHelp: "Liigu ajavalikute vahel nooleklahvidega. Ava häälevalikud Enteri või tühikuklahviga, vali nooltega ja kinnita Enteri või tühikuklahviga.",
      voteSavedStatus: "Hääl salvestatud: {status}.",
      voteCleared: "Hääl eemaldatud.",
      votesSaved: "Hääled salvestatud.",
      deleteVote: "Kustuta hääl",
      authNeeded: "Jätkamiseks sisesta nimi ja PIN-kood. Vajadusel luuakse uus kasutaja automaatselt.",
      authPrompt: "Kasuta nime ja PIN-koodi. Kui nime veel ei ole, luuakse uus kasutaja automaatselt.",
      name: "Nimi",
      pin: "PIN-kood",
      createdSuccess: "Küsitlus loodud.",
      pollUpdatedSuccess: "Küsitlus uuendatud.",
      voteDeleted: "Hääl kustutatud.",
      pollClosedSuccess: "Küsitlus suletud.",
      pollReopenedSuccess: "Küsitlus avati uuesti.",
      pollDeletedSuccess: "Küsitlus kustutatud.",
      loginSuccess: "Sisselogimine õnnestus.",
      createdLoginSuccess: "Loodi uus kasutaja ja logiti sisse.",
      logoutSuccess: "Väljalogimine õnnestus.",
      backToPollList: "Tagasi küsitluste nimekirja",
      backToProfile: "Tagasi minu andmete juurde",
      backToSelectedPoll: "Tagasi küsitluse juurde",
      backToCreatePoll: "Tagasi küsitluse loomise juurde",
      discardCreateConfirm: "Kas loobuda mustandist ja minna tagasi küsitluste nimekirja?",
      confirmDeletePoll: "Kas kustutada see küsitlus jäädavalt?",
      dismissFeedback: "Sulge teavitus",
      profileTitle: "Minu andmed",
      profileRefresh: "Värskenda",
      profileLoading: "Sinu andmeid laaditakse...",
      profileEmpty: "Andmeid pole veel laaditud.",
      profileDownloadJson: "Laadi JSON alla",
      profileDeleteOwnData: "Kustuta enda andmed",
      profileDeleteConfirm:
        "Kas kustutada nüüd sinu hääled ja kustutatavad küsitlused? Küsitlused, kus on teiste hääli, jäävad alles.",
      profileDeleteDone: "Enda andmed kustutati võimaluse piires.",
      profileDeleteDoneAccountRemoved: "Kõik isikuandmed eemaldati. Sinu konto kustutati.",
      profileDeletedVotes: "Kustutatud hääled",
      profileDeletedPolls: "Kustutatud küsitlused",
      profileRemainingPolls: "Alles jäänud loodud küsitlused",
      profileRemainingPollsWithOthers: "Alles jäänud küsitlused teiste häältega",
      profileIdentity: "Kasutaja andmed",
      profileStats: "Statistika",
      profileCreatedAt: "Loodud",
      profileUpdatedAt: "Uuendatud",
      profileCreatedPolls: "Loodud küsitlused",
      profileNoCreatedPolls: "Loodud küsitlusi pole.",
      profileVotes: "Minu hääled",
      profileNoVotes: "Hääli pole.",
      profileVoteTime: "Aeg",
      profileOpenPoll: "Ava küsitlus",
      profileVoteCount: "Häälte arv",
      profileDistinctVotedPollCount: "Küsitlused, milles oled hääletanud"
    }
  };

  const pollFormFieldOrder = [
    "title",
    "identifier",
    "timezone",
    "start_date",
    "end_date",
    "daily_start_hour",
    "daily_end_hour",
    "allowed_weekdays"
  ];

  const pollFormFieldIds = {
    create: {
      title: "poll-title",
      identifier: "poll-identifier",
      timezone: "poll-timezone",
      start_date: "start-date",
      end_date: "end-date",
      daily_start_hour: "daily-start-hour",
      daily_end_hour: "daily-end-hour"
    },
    edit: {
      title: "edit-title",
      identifier: "edit-identifier",
      timezone: "edit-timezone",
      start_date: "edit-start-date",
      end_date: "edit-end-date",
      daily_start_hour: "edit-daily-start-hour",
      daily_end_hour: "edit-daily-end-hour"
    }
  };

  const pollFormWeekdaySelectorByScope = {
    create: "#section-panel-create .weekday-item input",
    edit: "#section-panel-selected .poll-edit .weekday-item input"
  };

  const errorMessages = {
    invalid_json: {
      en: "Invalid request data.",
      fi: "Virheellinen pyyntödata.",
      sv: "Ogiltig begärandedata.",
      no: "Ugyldige forespørselsdata.",
      et: "Vigased päringuandmed."
    },
    invalid_credentials: {
      en: "Incorrect name or PIN.",
      fi: "Väärä nimi tai PIN-koodi.",
      sv: "Fel namn eller PIN-kod.",
      no: "Feil navn eller PIN-kode.",
      et: "Vale nimi või PIN-kood."
    },
    csrf_failed: {
      en: "Your session security token expired. Please try again.",
      fi: "Istunnon suojaustunniste vanheni. Yritä uudelleen.",
      sv: "Sessionens säkerhetstoken gick ut. Försök igen.",
      no: "Sikkerhetstokenet for økten utløp. Prøv igjen.",
      et: "Seansi turvatunnus aegus. Proovi uuesti."
    },
    authentication_required: {
      en: "Login is required for this action.",
      fi: "Tämä toiminto vaatii kirjautumisen.",
      sv: "Denna åtgärd kräver inloggning.",
      no: "Denne handlingen krever innlogging.",
      et: "See toiming nõuab sisselogimist."
    },
    poll_not_closed: {
      en: "Close the poll before deleting it.",
      fi: "Sulje kysely ennen poistamista.",
      sv: "Stäng omröstningen innan du tar bort den.",
      no: "Lukk avstemningen før du sletter den.",
      et: "Enne kustutamist sule küsitlus."
    },
    poll_closed: {
      en: "Poll is closed and votes can no longer be changed.",
      fi: "Kysely on suljettu eikä ääniä voi enää muuttaa.",
      sv: "Omröstningen är stängd och röster kan inte längre ändras.",
      no: "Avstemningen er lukket og stemmer kan ikke lenger endres.",
      et: "Küsitlus on suletud ja hääli ei saa enam muuta."
    },
    invalid_window: {
      en: "End date/time must be after start date/time.",
      fi: "Loppupäivän ja -ajan on oltava alun jälkeen.",
      sv: "Slutdatum/tid måste vara efter startdatum/tid.",
      no: "Sluttdato/-tid må være etter startdato/-tid.",
      et: "Lõppkuupäev/-aeg peab olema pärast alguskuupäeva/-aega."
    },
    invalid_date: {
      en: "Date format is invalid.",
      fi: "Päivämäärämuoto on virheellinen.",
      sv: "Datumformatet är ogiltigt.",
      no: "Ugyldig datoformat.",
      et: "Kuupäeva vorming on vigane."
    },
    invalid_date_range: {
      en: "End date must be on or after start date.",
      fi: "Loppupäivän on oltava sama tai myöhempi kuin alkupäivä.",
      sv: "Slutdatum måste vara samma eller senare än startdatum.",
      no: "Sluttdato må være lik eller etter startdato.",
      et: "Lõppkuupäev peab olema alguskuupäevaga sama või hilisem."
    },
    invalid_daily_hours: {
      en: "Daily end hour must be after daily start hour.",
      fi: "Päivän lopetustunnin on oltava aloitustunnin jälkeen.",
      sv: "Daglig sluttimme måste vara efter starttimme.",
      no: "Daglig sluttime må være etter daglig starttime.",
      et: "Päeva lõputund peab olema pärast algustundi."
    },
    invalid_weekdays: {
      en: "Select at least one weekday.",
      fi: "Valitse vähintään yksi viikonpäivä.",
      sv: "Välj minst en veckodag.",
      no: "Velg minst én ukedag.",
      et: "Vali vähemalt üks nädalapäev."
    },
    invalid_timezone: {
      en: "Timezone is invalid.",
      fi: "Aikavyöhyke on virheellinen.",
      sv: "Tidszonen är ogiltig.",
      no: "Tidssonen er ugyldig.",
      et: "Ajavöönd on vigane."
    },
    invalid_poll_identifier: {
      en: "Identifier may contain only A-Z, a-z, 0-9 and underscore (_).",
      fi: "Tunniste voi sisältää vain merkit A-Z, a-z, 0-9 ja alaviivan (_).",
      sv: "Identifieraren får bara innehålla A-Z, a-z, 0-9 och understreck (_).",
      no: "Identifikatoren kan bare inneholde A-Z, a-z, 0-9 og understrek (_).",
      et: "Tunnus võib sisaldada ainult märke A-Z, a-z, 0-9 ja alakriipsu (_)."
    },
    poll_identifier_taken: {
      en: "This identifier is already in use.",
      fi: "Tämä tunniste on jo käytössä.",
      sv: "Denna identifierare används redan.",
      no: "Denne identifikatoren er allerede i bruk.",
      et: "See tunnus on juba kasutusel."
    },
    too_many_options: {
      en: "Too many generated slots. Use a shorter time range or fewer days/hours.",
      fi: "Luotuja slotteja on liikaa. Lyhennä aikaväliä tai rajaa päiviä/tunteja.",
      sv: "För många genererade slots. Förkorta tidsintervallet eller begränsa dagar/timmar.",
      no: "For mange genererte tidsluker. Bruk et kortere tidsrom eller færre dager/timer.",
      et: "Genereeritud ajapesi on liiga palju. Kasuta lühemat vahemikku või vähem päevi/tunde."
    },
    forbidden: {
      en: "You do not have permission for this action.",
      fi: "Sinulla ei ole oikeutta tähän toimintoon.",
      sv: "Du har inte behörighet för denna åtgärd.",
      no: "Du har ikke tillatelse til denne handlingen.",
      et: "Sul puudub selle toimingu jaoks õigus."
    },
    schedule_conflicts_with_votes: {
      en: "You cannot remove time slots that already have votes.",
      fi: "Et voi poistaa aikaslotteja, joissa on jo ääniä.",
      sv: "Du kan inte ta bort tidslots som redan har röster.",
      no: "Du kan ikke fjerne tidsluker som allerede har stemmer.",
      et: "Sa ei saa eemaldada ajapesi, millel on juba hääled."
    }
  };

  const languageMap = {
    en: "en-GB",
    fi: "fi-FI",
    no: "no-NO",
    sv: "sv-SE",
    et: "et-EE"
  };

  function detectBrowserTimeZone() {
    try {
      const value = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (typeof value === "string" && value.trim()) {
        return value.trim();
      }
    } catch (_error) {
      // ignore
    }
    return "UTC";
  }

  function detectTimeZoneOptions() {
    try {
      if (typeof Intl.supportedValuesOf === "function") {
        const values = Intl.supportedValuesOf("timeZone");
        if (Array.isArray(values) && values.length) {
          return values;
        }
      }
    } catch (_error) {
      // ignore
    }
    return [
      "UTC",
      "Europe/Helsinki",
      "Europe/Stockholm",
      "Europe/London",
      "Europe/Berlin",
      "Europe/Paris",
      "America/New_York",
      "America/Chicago",
      "America/Denver",
      "America/Los_Angeles",
      "America/Phoenix",
      "Asia/Tokyo",
      "Asia/Seoul",
      "Asia/Singapore",
      "Australia/Sydney",
      "Pacific/Auckland"
    ];
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

  function parseWholeHourTimeKey(value) {
    if (typeof value !== "string") {
      return null;
    }
    const match = /^(\d{2}):(\d{2})$/.exec(value.trim());
    if (!match) {
      return null;
    }
    const hour = Number(match[1]);
    const minute = Number(match[2]);
    if (!Number.isInteger(hour) || !Number.isInteger(minute) || minute !== 0) {
      return null;
    }
    if (hour < 0 || hour > 23) {
      return null;
    }
    return hour;
  }

  function getTimeZoneNamePart(timeZone, style) {
    try {
      const parts = new Intl.DateTimeFormat("en-US", {
        timeZone,
        hour: "2-digit",
        minute: "2-digit",
        timeZoneName: style
      }).formatToParts(new Date());
      const tzPart = parts.find((part) => part.type === "timeZoneName");
      return tzPart ? tzPart.value : "";
    } catch (_error) {
      return "";
    }
  }

  function normalizeUtcOffsetLabel(value) {
    if (!value) {
      return "";
    }
    return value
      .replace(/^GMT/, "UTC")
      .replace(/^UTC$/, "UTC+0")
      .replace("−", "-");
  }

  function buildTimeZoneMeta(timeZone) {
    const shortName = getTimeZoneNamePart(timeZone, "short");
    const shortOffset = getTimeZoneNamePart(timeZone, "shortOffset");

    const offsetLabel = normalizeUtcOffsetLabel(shortOffset || shortName);
    const hasNameCode = shortName && !/^GMT|^UTC/.test(shortName);

    if (hasNameCode && offsetLabel && shortName !== offsetLabel) {
      return `${shortName} ${offsetLabel}`;
    }
    if (offsetLabel) {
      return offsetLabel;
    }
    if (shortName) {
      return shortName;
    }
    return "";
  }

  function safeLocalStorageGetItem(key) {
    try {
      if (typeof window === "undefined" || !window.localStorage) {
        return null;
      }
      return window.localStorage.getItem(key);
    } catch (error) {
      if (typeof console !== "undefined" && typeof console.warn === "function") {
        console.warn(`[TimePoll] localStorage.getItem failed for key "${key}".`, error);
      }
      return null;
    }
  }

  function safeLocalStorageSetItem(key, value) {
    try {
      if (typeof window === "undefined" || !window.localStorage) {
        return false;
      }
      window.localStorage.setItem(key, value);
      return true;
    } catch (error) {
      if (typeof console !== "undefined" && typeof console.warn === "function") {
        console.warn(`[TimePoll] localStorage.setItem failed for key "${key}".`, error);
      }
      return false;
    }
  }

  function getCookie(name) {
    const cookie = document.cookie
      .split(";")
      .map((item) => item.trim())
      .find((item) => item.startsWith(`${name}=`));
    return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : "";
  }

  function parseResponsePayload(rawText) {
    if (!rawText) {
      return {};
    }
    try {
      return JSON.parse(rawText);
    } catch (_error) {
      return {};
    }
  }

  function isCsrfFailureResponse(response, payload, rawText) {
    if (!response || response.status !== 403) {
      return false;
    }
    if (payload && payload.error === "csrf_failed") {
      return true;
    }
    const candidates = [];
    if (payload && typeof payload.detail === "string" && payload.detail) {
      candidates.push(payload.detail);
    }
    if (typeof rawText === "string" && rawText) {
      candidates.push(rawText);
    }
    return candidates.some((text) => /csrf/i.test(text) && /verification/i.test(text));
  }

  async function refreshCsrfCookie(force = false) {
    const currentToken = getCookie("csrftoken");
    if (!force && currentToken) {
      return currentToken;
    }
    if (!csrfRefreshPromise) {
      csrfRefreshPromise = fetch(csrfRefreshPath, {
        method: "GET",
        headers: { Accept: "application/json" },
        credentials: "same-origin"
      })
        .catch(() => null)
        .finally(() => {
          csrfRefreshPromise = null;
        });
    }
    await csrfRefreshPromise;
    return getCookie("csrftoken");
  }

  async function apiFetch(url, options = {}, retryState = {}) {
    const config = {
      method: String(options.method || "GET").toUpperCase(),
      headers: {
        Accept: "application/json",
        ...(options.headers || {})
      },
      credentials: "same-origin"
    };
    const unsafeMethod = config.method !== "GET" && config.method !== "HEAD";
    const allowCsrfRetry = retryState.allowCsrfRetry !== false;

    if (options.body !== undefined) {
      config.headers["Content-Type"] = "application/json";
      config.body = JSON.stringify(options.body);
    }

    if (unsafeMethod) {
      let token = getCookie("csrftoken");
      if (!token) {
        token = await refreshCsrfCookie(true);
      }
      if (token) {
        config.headers["X-CSRFToken"] = token;
      }
    }

    const response = await fetch(url, config);
    const responseText = await response.text();
    const data = parseResponsePayload(responseText);

    if (!response.ok) {
      if (unsafeMethod && allowCsrfRetry && isCsrfFailureResponse(response, data, responseText)) {
        await refreshCsrfCookie(true);
        return apiFetch(url, options, { allowCsrfRetry: false });
      }
      const err = new Error(data.detail || `HTTP ${response.status}`);
      err.status = response.status;
      err.payload = data;
      throw err;
    }

    return data;
  }

  function defaultPollForm() {
    return {
      identifier: "",
      title: "",
      description: "",
      start_date: "",
      end_date: "",
      daily_start_hour: 9,
      daily_end_hour: 17,
      allowed_weekdays: [0, 1, 2, 3, 4],
      timezone: detectBrowserTimeZone()
    };
  }

  function defaultCreateForm() {
    return defaultPollForm();
  }

  function editFormFromPoll(poll) {
    const fallback = defaultPollForm();
    if (!poll || typeof poll !== "object") {
      return fallback;
    }
    const weekdays = Array.isArray(poll.allowed_weekdays)
      ? poll.allowed_weekdays
          .map((item) => Number(item))
          .filter((item) => Number.isInteger(item) && item >= 0 && item <= 6)
      : fallback.allowed_weekdays;

    return {
      identifier:
        typeof poll.identifier === "string" && poll.identifier.trim() ? poll.identifier.trim() : fallback.identifier,
      title: typeof poll.title === "string" ? poll.title : fallback.title,
      description: typeof poll.description === "string" ? poll.description : fallback.description,
      start_date: typeof poll.start_date === "string" ? poll.start_date : fallback.start_date,
      end_date: typeof poll.end_date === "string" ? poll.end_date : fallback.end_date,
      daily_start_hour: Number.isInteger(poll.daily_start_hour) ? poll.daily_start_hour : fallback.daily_start_hour,
      daily_end_hour: Number.isInteger(poll.daily_end_hour) ? poll.daily_end_hour : fallback.daily_end_hour,
      allowed_weekdays: weekdays.length ? weekdays : fallback.allowed_weekdays,
      timezone: typeof poll.timezone === "string" && poll.timezone.trim() ? poll.timezone.trim() : fallback.timezone
    };
  }

  function rootFontSizePx() {
    if (typeof window === "undefined" || typeof document === "undefined") {
      return 16;
    }
    const fontSize = window.getComputedStyle(document.documentElement).fontSize;
    const parsed = Number.parseFloat(fontSize);
    return Number.isFinite(parsed) ? parsed : 16;
  }

  function estimateDayColumnWidthPx(viewportWidth) {
    void viewportWidth;
    return 8 * rootFontSizePx();
  }

  function estimateTimeColumnWidthPx(viewportWidth) {
    const rootPx = rootFontSizePx();
    return viewportWidth <= 860 ? 4.6 * rootPx : 5.2 * rootPx;
  }

  function cappedDayColumnWidthPx(containerWidth, referenceDayCount) {
    const viewportWidth = typeof window !== "undefined" ? window.innerWidth : containerWidth;
    const rootPx = rootFontSizePx();
    const timeWidth = estimateTimeColumnWidthPx(viewportWidth);
    const minWidth = 8 * rootPx;
    const maxWidth = 18 * rootPx;
    const normalizedDayCount = Number.isFinite(referenceDayCount) && referenceDayCount > 0
      ? Math.floor(referenceDayCount)
      : 1;
    const availableWidth = Math.max(0, containerWidth - timeWidth);
    const idealWidth = availableWidth / normalizedDayCount;
    return Math.min(maxWidth, Math.max(minWidth, idealWidth));
  }

  function visibleDayCountForWidth(containerWidth) {
    const viewportWidth = typeof window !== "undefined" ? window.innerWidth : containerWidth;
    const dayWidth = estimateDayColumnWidthPx(viewportWidth);
    const timeWidth = estimateTimeColumnWidthPx(viewportWidth);
    const availableWidth = Math.max(0, containerWidth - timeWidth);
    return Math.max(1, Math.floor(availableWidth / dayWidth));
  }

  function detectInitialVisibleDayCount() {
    if (typeof window === "undefined") {
      return 3;
    }
    return visibleDayCountForWidth(window.innerWidth);
  }

  const appDomains = window.TimePollAppDomains;
  const {
    createAuthProfileDomainMethods,
    createCalendarDomainMethods,
    createFormDomainMethods,
    createPollDomainMethods,
    createShellDomainMethods
  } = appDomains || {};

  if (
    typeof createAuthProfileDomainMethods !== "function"
    || typeof createCalendarDomainMethods !== "function"
    || typeof createFormDomainMethods !== "function"
    || typeof createPollDomainMethods !== "function"
    || typeof createShellDomainMethods !== "function"
  ) {
    showAppLogicLoadError();
    return;
  }

  const appMethods = {
    ...createShellDomainMethods({
      buildPollUrlState,
      errorMessages,
      extractPollIdFromSearch,
      languageMap,
      successFeedbackAutoCloseMs,
      translations
    }),
    ...createFormDomainMethods({
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
    }),
    ...createCalendarDomainMethods({
      apiFetch,
      calendarTimezonePreferenceStorageKeyForSession,
      cappedDayColumnWidthPx,
      collectDayOptionIdsFromRows,
      collectRowOptionIdsFromCells,
      estimateTimeColumnWidthPx,
      filterRowsForVisibleDaysAndMinYesVotes,
      filterWeekRowsByMinYesVotes,
      isVoteStatusValue,
      languageMap,
      loadCalendarTimezonePreferenceValue,
      matchesYesVoteFilter,
      nextVoteStatus,
      readOptionCount,
      safeLocalStorageGetItem,
      safeLocalStorageSetItem,
      serializeCalendarTimezonePreference,
      visibleDayCountForWidth,
      voteSyncDebounceMs
    }),
    ...createAuthProfileDomainMethods({
      apiFetch,
      safeLocalStorageGetItem,
      safeLocalStorageSetItem,
      translations
    }),
    ...createPollDomainMethods({
      apiFetch,
      defaultCreateForm
    })
  };

  const mountVueApp = () => {
    const { createApp } = window.Vue;

    createApp({
      delimiters: ["[[", "]]"],
      data() {
        return {
          language: "en",
          session: {
            authenticated: false,
            identity: null
          },
          polls: [],
          selectedPoll: null,
          profileSectionReturn: {
            section: "list",
            focusId: ""
          },
          selectedSectionReturn: {
            section: "list",
            focusId: ""
          },
          activeSection: "list",
          voteDraft: {},
          createForm: defaultCreateForm(),
          createSectionReturnFocusId: "open-create-poll",
          editForm: null,
          formErrors: {
            create: {},
            edit: {}
          },
          formTouched: {
            create: {},
            edit: {}
          },
          showAllFormErrors: {
            create: false,
            edit: false
          },
          isEditingPoll: false,
          isApplyingEditTimezoneAutoGrow: false,
          isApplyingEditTimezoneProgrammaticChange: false,
          editAutoGrowNotice: "",
          editCommittedTimezone: "",
          showEditTimezoneConfirmDialog: false,
          pendingEditTimezoneAutoGrow: null,
          timezoneOptions: detectTimeZoneOptions(),
          timezoneMetaCache: {},
          browserTimeZone: detectBrowserTimeZone(),
          calendarTimezoneMode: "poll",
          calendarCustomTimezone: detectBrowserTimeZone(),
          voteDisplayMode: "own",
          showCalendarTimezoneSuggestions: false,
          showTimezoneSuggestions: false,
          showEditTimezoneSuggestions: false,
          activeTimezoneSuggestionIndex: -1,
          activeEditTimezoneSuggestionIndex: -1,
          activeCalendarTimezoneSuggestionIndex: -1,
          profileData: null,
          profileLoading: false,
          profileDeleting: false,
          profileVoteDeletingOptionIds: {},
          profileDeleteSummary: null,
          authForm: {
            name: "",
            pin: ""
          },
          showAuthDialog: false,
          pendingAction: null,
          pollListNeedsRefresh: false,
          errorMessage: "",
          successMessage: "",
          successFeedbackTimerId: null,
          voteStatusAnnouncement: "",
          bulkMenu: null,
          voteCellMenuPreview: null,
          activeVoteCellId: "",
          calendarWrapWidth: typeof window !== "undefined" ? window.innerWidth : 0,
          visibleDayCount: detectInitialVisibleDayCount(),
          minYesVotesFilter: 0
        };
      },
      computed: {
        canVoteInPoll() {
          return Boolean(this.selectedPoll && !this.selectedPoll.is_closed);
        },
        profileCreatedPolls() {
          if (!this.profileData || !Array.isArray(this.profileData.created_polls)) {
            return [];
          }
          return this.profileData.created_polls;
        },
        profileVotes() {
          if (!this.profileData || !Array.isArray(this.profileData.votes)) {
            return [];
          }
          return this.profileData.votes;
        },
        profileSectionReturnSection() {
          const section = this.profileSectionReturn && typeof this.profileSectionReturn.section === "string"
            ? this.profileSectionReturn.section
            : "list";
          if (section === "selected") {
            return this.selectedPoll ? "selected" : "list";
          }
          if (section === "create") {
            return "create";
          }
          return "list";
        },
        profileSectionBackLabel() {
          if (this.profileSectionReturnSection === "selected") {
            return this.t("backToSelectedPoll");
          }
          if (this.profileSectionReturnSection === "create") {
            return this.t("backToCreatePoll");
          }
          return this.t("backToPollList");
        },
        selectedSectionReturnSection() {
          if (this.selectedSectionReturn && this.selectedSectionReturn.section === "profile" && this.session.authenticated) {
            return "profile";
          }
          return "list";
        },
        selectedSectionBackLabel() {
          return this.selectedSectionReturnSection === "profile"
            ? this.t("backToProfile")
            : this.t("backToPollList");
        },
        maxYesVotesInPoll() {
          if (!this.selectedPoll || !Array.isArray(this.selectedPoll.options)) {
            return 0;
          }
          let maxVotes = 0;
          for (const option of this.selectedPoll.options) {
            const yesCount = this.optionCount(option, "yes");
            if (yesCount > maxVotes) {
              maxVotes = yesCount;
            }
          }
          return maxVotes;
        },
        yesVotesFilterOptions() {
          const maxVotes = Number.isInteger(this.maxYesVotesInPoll) && this.maxYesVotesInPoll > 0
            ? this.maxYesVotesInPoll
            : 0;
          return Array.from({ length: maxVotes + 1 }, (_, index) => index);
        },
        startHourOptions() {
          return Array.from({ length: 24 }, (_, index) => index);
        },
        endHourOptions() {
          return Array.from({ length: 24 }, (_, index) => index + 1);
        },
        weekdayOptions() {
          return [
            { value: 0, label: this.t("weekdayMon") },
            { value: 1, label: this.t("weekdayTue") },
            { value: 2, label: this.t("weekdayWed") },
            { value: 3, label: this.t("weekdayThu") },
            { value: 4, label: this.t("weekdayFri") },
            { value: 5, label: this.t("weekdaySat") },
            { value: 6, label: this.t("weekdaySun") }
          ];
        },
        filteredTimezoneOptions() {
          return this.buildFilteredTimezoneOptions(this.timezoneInputValue("create"));
        },
        filteredEditTimezoneOptions() {
          return this.buildFilteredTimezoneOptions(this.timezoneInputValue("edit"));
        },
        filteredCalendarTimezoneOptions() {
          return this.buildFilteredTimezoneOptions(this.timezoneInputValue("calendar"));
        },
        activeCreateTimezoneSuggestionId() {
          return this.activeTimezoneSuggestionIdForScope("create");
        },
        activeEditTimezoneSuggestionId() {
          return this.activeTimezoneSuggestionIdForScope("edit");
        },
        activeCalendarTimezoneSuggestionId() {
          return this.activeTimezoneSuggestionIdForScope("calendar");
        },
        selectedTimezoneDisplay() {
          return this.timezoneDisplay(this.createForm.timezone);
        },
        editTimezoneDisplay() {
          if (!this.editForm) {
            return "";
          }
          return this.timezoneDisplay(this.editForm.timezone);
        },
        editVotedDateBounds() {
          if (!this.selectedPoll || !Array.isArray(this.selectedPoll.options) || !this.editForm) {
            return {
              earliestDay: "",
              latestDay: "",
              hasVotes: false
            };
          }

          const fallbackTimeZone = this.selectedPoll && typeof this.selectedPoll.timezone === "string"
            ? this.selectedPoll.timezone
            : "";
          const timeZone = this.normalizeKnownTimeZone(this.editForm.timezone)
            || this.normalizeKnownTimeZone(fallbackTimeZone)
            || "UTC";
          let earliestDay = "";
          let latestDay = "";

          for (const option of this.selectedPoll.options) {
            if (!this.pollOptionHasVotes(option)) {
              continue;
            }
            const dateParts = this.timezoneDateParts(option.starts_at, timeZone);
            if (!dateParts || !dateParts.dayKey) {
              continue;
            }
            const dayKey = dateParts.dayKey;
            if (!earliestDay || dayKey < earliestDay) {
              earliestDay = dayKey;
            }
            if (!latestDay || dayKey > latestDay) {
              latestDay = dayKey;
            }
          }

          return {
            earliestDay,
            latestDay,
            hasVotes: Boolean(earliestDay && latestDay)
          };
        },
        editStartDateMax() {
          if (!this.editForm) {
            return "";
          }
          const candidates = [];
          const endDateRaw = String(this.editForm.end_date || "").trim();
          if (parseIsoDateValue(endDateRaw)) {
            candidates.push(endDateRaw);
          }
          if (this.editVotedDateBounds.earliestDay) {
            candidates.push(this.editVotedDateBounds.earliestDay);
          }
          if (!candidates.length) {
            return "";
          }
          return candidates.sort((a, b) => a.localeCompare(b))[0];
        },
        editEndDateMin() {
          if (!this.editForm) {
            return "";
          }
          const candidates = [];
          const startDateRaw = String(this.editForm.start_date || "").trim();
          if (parseIsoDateValue(startDateRaw)) {
            candidates.push(startDateRaw);
          }
          if (this.editVotedDateBounds.latestDay) {
            candidates.push(this.editVotedDateBounds.latestDay);
          }
          if (!candidates.length) {
            return "";
          }
          return candidates.sort((a, b) => b.localeCompare(a))[0];
        },
        editStartDateConstraintHints() {
          if (!this.editForm) {
            return [];
          }
          if (this.editVotedDateBounds.earliestDay) {
            return [
              this.formatTemplate(this.t("editStartDateBoundByVotes"), {
                date: this.formatDayLongLabel(this.editVotedDateBounds.earliestDay)
              })
            ];
          }
          const endDateRaw = String(this.editForm.end_date || "").trim();
          if (parseIsoDateValue(endDateRaw)) {
            return [this.t("editStartDateBoundByEndDate")];
          }
          return [];
        },
        editEndDateConstraintHints() {
          if (!this.editForm) {
            return [];
          }
          if (this.editVotedDateBounds.latestDay) {
            return [
              this.formatTemplate(this.t("editEndDateBoundByVotes"), {
                date: this.formatDayLongLabel(this.editVotedDateBounds.latestDay)
              })
            ];
          }
          const startDateRaw = String(this.editForm.start_date || "").trim();
          if (parseIsoDateValue(startDateRaw)) {
            return [this.t("editEndDateBoundByStartDate")];
          }
          return [];
        },
        editVotedHourBounds() {
          if (!this.selectedPoll || !Array.isArray(this.selectedPoll.options) || !this.editForm) {
            return {
              earliestHour: null,
              latestHour: null,
              minEndHour: null,
              hasVotes: false
            };
          }

          const fallbackTimeZone = this.selectedPoll && typeof this.selectedPoll.timezone === "string"
            ? this.selectedPoll.timezone
            : "";
          const timeZone = this.normalizeKnownTimeZone(this.editForm.timezone)
            || this.normalizeKnownTimeZone(fallbackTimeZone)
            || "UTC";
          let earliestHour = null;
          let latestHour = null;

          for (const option of this.selectedPoll.options) {
            if (!this.pollOptionHasVotes(option)) {
              continue;
            }
            const dateParts = this.timezoneDateParts(option.starts_at, timeZone);
            const hour = parseWholeHourTimeKey(dateParts && dateParts.timeKey ? dateParts.timeKey : "");
            if (!Number.isInteger(hour)) {
              continue;
            }
            if (earliestHour === null || hour < earliestHour) {
              earliestHour = hour;
            }
            if (latestHour === null || hour > latestHour) {
              latestHour = hour;
            }
          }

          return {
            earliestHour,
            latestHour,
            minEndHour: Number.isInteger(latestHour) ? Math.min(24, latestHour + 1) : null,
            hasVotes: earliestHour !== null && latestHour !== null
          };
        },
        editStartHourMax() {
          if (!this.editForm) {
            return null;
          }
          const candidates = [];
          if (Number.isInteger(this.editForm.daily_end_hour)) {
            candidates.push(this.editForm.daily_end_hour - 1);
          }
          if (Number.isInteger(this.editVotedHourBounds.earliestHour)) {
            candidates.push(this.editVotedHourBounds.earliestHour);
          }
          if (!candidates.length) {
            return null;
          }
          return Math.min(...candidates);
        },
        editEndHourMin() {
          if (!this.editForm) {
            return null;
          }
          const candidates = [];
          if (Number.isInteger(this.editForm.daily_start_hour)) {
            candidates.push(this.editForm.daily_start_hour + 1);
          }
          if (Number.isInteger(this.editVotedHourBounds.minEndHour)) {
            candidates.push(this.editVotedHourBounds.minEndHour);
          }
          if (!candidates.length) {
            return null;
          }
          return Math.max(...candidates);
        },
        editStartHourOptions() {
          const maxHour = this.editStartHourMax;
          return this.startHourOptions.map((hour) => ({
            value: hour,
            disabled: Number.isInteger(maxHour) && hour > maxHour
          }));
        },
        editEndHourOptions() {
          const minHour = this.editEndHourMin;
          return this.endHourOptions.map((hour) => ({
            value: hour,
            disabled: Number.isInteger(minHour) && hour < minHour
          }));
        },
        editStartHourConstraintHints() {
          if (!this.editForm) {
            return [];
          }
          if (Number.isInteger(this.editVotedHourBounds.earliestHour)) {
            return [
              this.formatTemplate(this.t("editStartHourBoundByVotes"), {
                hour: this.hourLabel(this.editVotedHourBounds.earliestHour)
              })
            ];
          }
          if (Number.isInteger(this.editForm.daily_end_hour)) {
            return [this.t("editStartHourBoundByEndHour")];
          }
          return [];
        },
        editEndHourConstraintHints() {
          if (!this.editForm) {
            return [];
          }
          if (Number.isInteger(this.editVotedHourBounds.minEndHour)) {
            return [
              this.formatTemplate(this.t("editEndHourBoundByVotes"), {
                hour: this.hourLabel(this.editVotedHourBounds.minEndHour)
              })
            ];
          }
          if (Number.isInteger(this.editForm.daily_start_hour)) {
            return [this.t("editEndHourBoundByStartHour")];
          }
          return [];
        },
        editLockedWeekdayValues() {
          if (!this.selectedPoll || !Array.isArray(this.selectedPoll.options) || !this.editForm) {
            return [];
          }

          const fallbackTimeZone = this.selectedPoll && typeof this.selectedPoll.timezone === "string"
            ? this.selectedPoll.timezone
            : "";
          const timeZone = this.normalizeKnownTimeZone(this.editForm.timezone)
            || this.normalizeKnownTimeZone(fallbackTimeZone)
            || "UTC";
          const lockedWeekdays = new Set();

          for (const option of this.selectedPoll.options) {
            if (!this.pollOptionHasVotes(option)) {
              continue;
            }
            const dateParts = this.timezoneDateParts(option.starts_at, timeZone);
            if (!dateParts || !dateParts.dayKey) {
              continue;
            }
            const optionDate = parseIsoDateValue(dateParts.dayKey);
            if (!optionDate) {
              continue;
            }
            const weekdayJs = optionDate.getUTCDay();
            const weekday = weekdayJs === 0 ? 6 : weekdayJs - 1;
            lockedWeekdays.add(weekday);
          }

          return Array.from(lockedWeekdays).sort((a, b) => a - b);
        },
        editAllowedWeekdaysConstraintHints() {
          if (!this.editLockedWeekdayValues.length) {
            return [];
          }
          const labels = this.editLockedWeekdayValues.map((weekday) => {
            const option = this.weekdayOptions.find((item) => item.value === weekday);
            return option ? option.label : String(weekday);
          });
          return [
            this.formatTemplate(this.t("editAllowedWeekdaysBoundByVotes"), {
              days: labels.join(", ")
            })
          ];
        },
        pollCalendarTimezone() {
          const pollTimeZone = this.selectedPoll && this.selectedPoll.timezone ? this.selectedPoll.timezone : "";
          const normalized = this.normalizeKnownTimeZone(pollTimeZone);
          return normalized || "UTC";
        },
        browserCalendarTimezone() {
          const normalized = this.normalizeKnownTimeZone(this.browserTimeZone);
          return normalized || this.pollCalendarTimezone;
        },
        showBrowserTimezoneOption() {
          return this.browserCalendarTimezone.toLowerCase() !== this.pollCalendarTimezone.toLowerCase();
        },
        customCalendarTimezoneDisplay() {
          const normalizedCustom = this.normalizeKnownTimeZone(this.calendarCustomTimezone);
          if (!normalizedCustom) {
            return "";
          }
          return this.timezoneDisplay(normalizedCustom);
        },
        calendarDisplayTimezone() {
          if (this.calendarTimezoneMode === "browser" && this.showBrowserTimezoneOption) {
            return this.browserCalendarTimezone;
          }
          if (this.calendarTimezoneMode === "custom") {
            const normalizedCustom = this.normalizeKnownTimeZone(this.calendarCustomTimezone);
            if (normalizedCustom) {
              return normalizedCustom;
            }
          }
          return this.pollCalendarTimezone;
        },
        calendarWeeks() {
          if (!this.selectedPoll || !Array.isArray(this.selectedPoll.options) || !this.selectedPoll.options.length) {
            return [];
          }

          const timeZone = this.calendarDisplayTimezone || "UTC";
          const dayMap = new Map();
          const timeSet = new Set();
          const optionBuckets = new Map();

          for (const option of this.selectedPoll.options) {
            const dateParts = this.timezoneDateParts(option.starts_at, timeZone);
            if (!dateParts) {
              continue;
            }
            const dayKey = dateParts.dayKey;
            const timeKey = dateParts.timeKey;
            if (!dayMap.has(dayKey)) {
              dayMap.set(dayKey, {
                key: dayKey,
                label: this.formatDayLabel(dayKey),
                longLabel: this.formatDayLongLabel(dayKey)
              });
            }
            timeSet.add(timeKey);
            const optionBucketKey = `${dayKey}|${timeKey}`;
            const existingBucket = optionBuckets.get(optionBucketKey) || [];
            existingBucket.push(option);
            optionBuckets.set(optionBucketKey, existingBucket);
          }

          const dayKeys = Array.from(dayMap.keys()).sort((a, b) => a.localeCompare(b));
          const timeKeys = Array.from(timeSet).sort((a, b) => a.localeCompare(b));
          for (const bucket of optionBuckets.values()) {
            bucket.sort((left, right) => String(left && left.starts_at || "").localeCompare(String(right && right.starts_at || "")));
          }

          const weeksMap = new Map();
          for (const dayKey of dayKeys) {
            const weekKey = this.weekStartKey(dayKey);
            if (!weeksMap.has(weekKey)) {
              weeksMap.set(weekKey, {
                key: weekKey,
                title: this.formatWeekTitle(weekKey),
                days: []
              });
            }
            weeksMap.get(weekKey).days.push(dayMap.get(dayKey));
          }

          const weeks = Array.from(weeksMap.values()).sort((a, b) => a.key.localeCompare(b.key));
          for (const week of weeks) {
            const rows = [];
            for (const timeKey of timeKeys) {
              const maxBucketLength = week.days.reduce((currentMax, day) => {
                const bucketKey = `${day.key}|${timeKey}`;
                const bucket = optionBuckets.get(bucketKey) || [];
                return Math.max(currentMax, bucket.length);
              }, 0);
              for (let occurrenceIndex = 0; occurrenceIndex < maxBucketLength; occurrenceIndex += 1) {
                const cells = {};
                for (const day of week.days) {
                  const bucketKey = `${day.key}|${timeKey}`;
                  const bucket = optionBuckets.get(bucketKey) || [];
                  const option = bucket[occurrenceIndex];
                  if (option) {
                    cells[day.key] = option;
                  }
                }
            if (Object.keys(cells).length > 0) {
                  rows.push({
                    key: `${week.key}-${timeKey}-${occurrenceIndex}`,
                    timeKey,
                    occurrenceIndex,
                    occurrenceCount: maxBucketLength,
                    cells
                  });
                }
              }
            }
            week.rows = rows;
          }

          return weeks;
        }
      },
      watch: {
        calendarWeeks() {
          this.syncActiveVoteCell();
          this.$nextTick(() => {
            this.updateVisibleDayCount();
          });
        },
        maxYesVotesInPoll(newValue) {
          const normalizedMax = Number.isInteger(newValue) && newValue > 0 ? newValue : 0;
          if (this.minYesVotesFilter > normalizedMax) {
            this.minYesVotesFilter = normalizedMax;
          }
          if (this.minYesVotesFilter < 0) {
            this.minYesVotesFilter = 0;
          }
        },
        minYesVotesFilter() {
          this.syncActiveVoteCell();
        },
        calendarTimezoneMode(newValue) {
          if (newValue !== "custom") {
            this.showCalendarTimezoneSuggestions = false;
            this.savePreferredCalendarTimezonePreference();
            return;
          }
          if (!this.normalizeKnownTimeZone(this.calendarCustomTimezone)) {
            this.calendarCustomTimezone = this.browserCalendarTimezone;
          }
          this.savePreferredCalendarTimezonePreference();
        },
        showBrowserTimezoneOption(isVisible) {
          if (!isVisible && this.calendarTimezoneMode === "browser") {
            this.calendarTimezoneMode = "poll";
          }
        },
        showTimezoneSuggestions(isVisible) {
          if (!isVisible) {
            this.activeTimezoneSuggestionIndex = -1;
            return;
          }
          this.syncTimezoneSuggestionIndex("create");
        },
        showEditTimezoneSuggestions(isVisible) {
          if (!isVisible) {
            this.activeEditTimezoneSuggestionIndex = -1;
            return;
          }
          this.syncTimezoneSuggestionIndex("edit");
        },
        showCalendarTimezoneSuggestions(isVisible) {
          if (!isVisible) {
            this.activeCalendarTimezoneSuggestionIndex = -1;
            return;
          }
          this.syncTimezoneSuggestionIndex("calendar");
        },
        "editForm.title"(newValue, oldValue) {
          if (!this.isEditingPoll || oldValue === null || oldValue === undefined || newValue === oldValue) {
            return;
          }
          this.handleFormFieldChange("title", "edit");
        },
        "editForm.identifier"(newValue, oldValue) {
          if (!this.isEditingPoll || oldValue === null || oldValue === undefined || newValue === oldValue) {
            return;
          }
          this.handleFormFieldChange("identifier", "edit");
        },
        "editForm.timezone"(newValue, oldValue) {
          if (
            !this.isEditingPoll
            || this.isApplyingEditTimezoneProgrammaticChange
            || oldValue === null
            || oldValue === undefined
            || newValue === oldValue
          ) {
            return;
          }
          this.editAutoGrowNotice = "";
        },
        "editForm.start_date"(newValue, oldValue) {
          if (
            !this.isEditingPoll
            || this.isApplyingEditTimezoneAutoGrow
            || oldValue === null
            || oldValue === undefined
            || newValue === oldValue
          ) {
            return;
          }
          this.handleFormFieldChange("start_date", "edit");
        },
        "editForm.end_date"(newValue, oldValue) {
          if (
            !this.isEditingPoll
            || this.isApplyingEditTimezoneAutoGrow
            || oldValue === null
            || oldValue === undefined
            || newValue === oldValue
          ) {
            return;
          }
          this.handleFormFieldChange("end_date", "edit");
        },
        "editForm.daily_start_hour"(newValue, oldValue) {
          if (
            !this.isEditingPoll
            || this.isApplyingEditTimezoneAutoGrow
            || oldValue === null
            || oldValue === undefined
            || newValue === oldValue
          ) {
            return;
          }
          this.handleFormFieldChange("daily_start_hour", "edit");
        },
        "editForm.daily_end_hour"(newValue, oldValue) {
          if (
            !this.isEditingPoll
            || this.isApplyingEditTimezoneAutoGrow
            || oldValue === null
            || oldValue === undefined
            || newValue === oldValue
          ) {
            return;
          }
          this.handleFormFieldChange("daily_end_hour", "edit");
        },
        "editForm.allowed_weekdays"(newValue, oldValue) {
          if (
            !this.isEditingPoll
            || this.isApplyingEditTimezoneAutoGrow
            || !Array.isArray(newValue)
            || !Array.isArray(oldValue)
          ) {
            return;
          }
          if (newValue.join(",") === oldValue.join(",")) {
            return;
          }
          this.handleFormFieldChange("allowed_weekdays", "edit");
        }
      },
      methods: appMethods,
      async mounted() {
        this._onWindowResize = () => {
          this.updateVisibleDayCount();
        };
        this._onPopState = () => {
          this.applyPollFromUrl({ replace: true });
        };
        window.addEventListener("resize", this._onWindowResize);
        window.addEventListener("popstate", this._onPopState);
        await this.fetchSession();
        await this.changeLanguage();
        await this.fetchPolls();
        await this.applyPollFromUrl({ replace: true });
        this.$nextTick(() => {
          this.updateVisibleDayCount();
          if (
            this.activeSection === "list"
            && this.selectedPoll === null
            && (
              document.activeElement === document.body
              || document.activeElement === document.documentElement
            )
          ) {
            this.focusPollListHeading();
          }
        });
        window.__timePollAppMounted = true;
      },
      beforeUnmount() {
        window.__timePollAppMounted = false;
        this.clearSuccessFeedbackTimer();
        this.resetVoteSyncState();
        if (this._onWindowResize) {
          window.removeEventListener("resize", this._onWindowResize);
          this._onWindowResize = null;
        }
        if (this._onPopState) {
          window.removeEventListener("popstate", this._onPopState);
          this._onPopState = null;
        }
      }
    }).mount("#app");
  };

  const waitForVueAndMount = (attemptsLeft = 60) => {
    if (window.Vue) {
      mountVueApp();
      return;
    }
    if (attemptsLeft <= 0) {
      const root = document.getElementById("app");
      if (root) {
        root.innerHTML = "<p class='feedback error'>Vue.js did not load.</p>";
      }
      return;
    }
    window.setTimeout(() => waitForVueAndMount(attemptsLeft - 1), 100);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => waitForVueAndMount());
  } else {
    waitForVueAndMount();
  }

})();
