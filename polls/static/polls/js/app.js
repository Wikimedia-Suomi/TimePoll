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
    isVoteStatusValue,
    loadCalendarTimezonePreferenceValue,
    matchesYesVoteFilter,
    nextVoteStatus,
    optionHasVotes,
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
    || typeof isVoteStatusValue !== "function"
    || typeof loadCalendarTimezonePreferenceValue !== "function"
    || typeof matchesYesVoteFilter !== "function"
    || typeof nextVoteStatus !== "function"
    || typeof optionHasVotes !== "function"
    || typeof readOptionCount !== "function"
    || typeof serializeCalendarTimezonePreference !== "function"
    || typeof toggleWeekdaySelection !== "function"
  ) {
    showAppLogicLoadError();
    return;
  }

  const successFeedbackAutoCloseMs = 3500;

const translations = {
    en: {
      appTitle: "TimePoll",
      appSubtitle: "Vote on times to agree on schedules.",
      language: "Language",
      hello: "Hello,",
      login: "Login",
      logout: "Logout",
      register: "Register",
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
      deleteVote: "Delete vote",
      authNeeded: "Enter your name and PIN to continue. A new user is created automatically if needed.",
      authPrompt: "Use your name and PIN. If the name does not exist yet, a new user is created automatically.",
      name: "Name",
      pin: "PIN code",
      switchToLogin: "Already registered? Login",
      switchToRegister: "Need an account? Register",
      createdSuccess: "Poll created successfully.",
      pollUpdatedSuccess: "Poll updated successfully.",
      voteDeleted: "Vote deleted.",
      pollClosedSuccess: "Poll closed.",
      pollReopenedSuccess: "Poll reopened.",
      pollDeletedSuccess: "Poll deleted.",
      loginSuccess: "Logged in.",
      createdLoginSuccess: "New user created and logged in.",
      registerSuccess: "Registered and logged in.",
      logoutSuccess: "Logged out.",
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
      register: "Rekisteröidy",
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
      deleteVote: "Poista ääni",
      authNeeded: "Syötä nimi ja PIN-koodi jatkaaksesi. Uusi käyttäjä luodaan automaattisesti tarvittaessa.",
      authPrompt: "Käytä nimeä ja PIN-koodia. Jos nimeä ei ole vielä olemassa, uusi käyttäjä luodaan automaattisesti.",
      name: "Nimi",
      pin: "PIN-koodi",
      switchToLogin: "Onko tili jo? Kirjaudu",
      switchToRegister: "Tarvitsetko tilin? Rekisteröidy",
      createdSuccess: "Kysely luotu.",
      pollUpdatedSuccess: "Kysely päivitetty.",
      voteDeleted: "Ääni poistettu.",
      pollClosedSuccess: "Kysely suljettu.",
      pollReopenedSuccess: "Kysely avattu uudelleen.",
      pollDeletedSuccess: "Kysely poistettu.",
      loginSuccess: "Kirjautuminen onnistui.",
      createdLoginSuccess: "Uusi käyttäjä luotiin ja kirjautuminen onnistui.",
      registerSuccess: "Rekisteröityminen onnistui.",
      logoutSuccess: "Uloskirjautuminen onnistui.",
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
      register: "Registrera",
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
      deleteVote: "Ta bort röst",
      authNeeded: "Ange namn och PIN-kod för att fortsätta. En ny användare skapas automatiskt vid behov.",
      authPrompt: "Använd namn och PIN-kod. Om namnet inte finns skapas en ny användare automatiskt.",
      name: "Namn",
      pin: "PIN-kod",
      switchToLogin: "Har du konto? Logga in",
      switchToRegister: "Behöver du konto? Registrera",
      createdSuccess: "Omröstning skapad.",
      pollUpdatedSuccess: "Omröstning uppdaterad.",
      voteDeleted: "Röst borttagen.",
      pollClosedSuccess: "Omröstning stängd.",
      pollReopenedSuccess: "Omröstning öppnad igen.",
      pollDeletedSuccess: "Omröstning borttagen.",
      loginSuccess: "Inloggad.",
      createdLoginSuccess: "Ny användare skapad och inloggad.",
      registerSuccess: "Registrerad och inloggad.",
      logoutSuccess: "Utloggad.",
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
      register: "Registrer",
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
      deleteVote: "Slett stemme",
      authNeeded: "Skriv inn navn og PIN-kode for å fortsette. En ny bruker opprettes automatisk ved behov.",
      authPrompt: "Bruk navn og PIN-kode. Hvis navnet ikke finnes ennå, opprettes en ny bruker automatisk.",
      name: "Navn",
      pin: "PIN-kode",
      switchToLogin: "Har du allerede konto? Logg inn",
      switchToRegister: "Trenger du en konto? Registrer",
      createdSuccess: "Avstemning opprettet.",
      pollUpdatedSuccess: "Avstemning oppdatert.",
      voteDeleted: "Stemme slettet.",
      pollClosedSuccess: "Avstemning lukket.",
      pollReopenedSuccess: "Avstemning åpnet på nytt.",
      pollDeletedSuccess: "Avstemning slettet.",
      loginSuccess: "Innlogget.",
      createdLoginSuccess: "Ny bruker opprettet og innlogget.",
      registerSuccess: "Registrert og innlogget.",
      logoutSuccess: "Utlogget.",
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
      register: "Registreeru",
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
      deleteVote: "Kustuta hääl",
      authNeeded: "Jätkamiseks sisesta nimi ja PIN-kood. Vajadusel luuakse uus kasutaja automaatselt.",
      authPrompt: "Kasuta nime ja PIN-koodi. Kui nime veel ei ole, luuakse uus kasutaja automaatselt.",
      name: "Nimi",
      pin: "PIN-kood",
      switchToLogin: "Konto on olemas? Logi sisse",
      switchToRegister: "Vajad kontot? Registreeru",
      createdSuccess: "Küsitlus loodud.",
      pollUpdatedSuccess: "Küsitlus uuendatud.",
      voteDeleted: "Hääl kustutatud.",
      pollClosedSuccess: "Küsitlus suletud.",
      pollReopenedSuccess: "Küsitlus avati uuesti.",
      pollDeletedSuccess: "Küsitlus kustutatud.",
      loginSuccess: "Sisselogimine õnnestus.",
      createdLoginSuccess: "Loodi uus kasutaja ja logiti sisse.",
      registerSuccess: "Registreerimine õnnestus.",
      logoutSuccess: "Väljalogimine õnnestus.",
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
    name_taken: {
      en: "This name is already registered.",
      fi: "Tämä nimi on jo rekisteröity.",
      sv: "Detta namn är redan registrerat.",
      no: "Dette navnet er allerede registrert.",
      et: "See nimi on juba registreeritud."
    },
    invalid_credentials: {
      en: "Incorrect name or PIN.",
      fi: "Väärä nimi tai PIN-koodi.",
      sv: "Fel namn eller PIN-kod.",
      no: "Feil navn eller PIN-kode.",
      et: "Vale nimi või PIN-kood."
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

  async function apiFetch(url, options = {}) {
    const config = {
      method: options.method || "GET",
      headers: {
        Accept: "application/json",
        ...(options.headers || {})
      },
      credentials: "same-origin"
    };

    if (options.body !== undefined) {
      config.headers["Content-Type"] = "application/json";
      config.body = JSON.stringify(options.body);
    }

    if (config.method !== "GET" && config.method !== "HEAD") {
      const token = getCookie("csrftoken");
      if (token) {
        config.headers["X-CSRFToken"] = token;
      }
    }

    const response = await fetch(url, config);
    let data = {};
    try {
      data = await response.json();
    } catch (_error) {
      data = {};
    }

    if (!response.ok) {
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
          activeSection: "list",
          voteDraft: {},
          createForm: defaultCreateForm(),
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
          errorMessage: "",
          successMessage: "",
          successFeedbackTimerId: null,
          bulkMenu: null,
          calendarWrapWidth: typeof window !== "undefined" ? window.innerWidth : 0,
          visibleDayCount: detectInitialVisibleDayCount(),
          minYesVotesFilter: 0,
          savingVoteOptionIds: {}
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
          const options = this.timezoneOptions.map((tz) => {
            const meta = this.timezoneMeta(tz);
            const label = meta ? `${tz} ${meta}` : tz;
            return { id: tz, meta, label };
          });
          const rawQuery = (this.createForm.timezone || "").trim().toLowerCase();
          if (!rawQuery) {
            return options.slice(0, 200);
          }
          return options
            .filter((item) => item.label.toLowerCase().includes(rawQuery))
            .slice(0, 200);
        },
        filteredEditTimezoneOptions() {
          const options = this.timezoneOptions.map((tz) => {
            const meta = this.timezoneMeta(tz);
            const label = meta ? `${tz} ${meta}` : tz;
            return { id: tz, meta, label };
          });
          const rawQuery = this.editForm && typeof this.editForm.timezone === "string"
            ? this.editForm.timezone.trim().toLowerCase()
            : "";
          if (!rawQuery) {
            return options.slice(0, 200);
          }
          return options
            .filter((item) => item.label.toLowerCase().includes(rawQuery))
            .slice(0, 200);
        },
        filteredCalendarTimezoneOptions() {
          const options = this.timezoneOptions.map((tz) => {
            const meta = this.timezoneMeta(tz);
            const label = meta ? `${tz} ${meta}` : tz;
            return { id: tz, meta, label };
          });
          const rawQuery = (this.calendarCustomTimezone || "").trim().toLowerCase();
          if (!rawQuery) {
            return options.slice(0, 200);
          }
          return options
            .filter((item) => item.label.toLowerCase().includes(rawQuery))
            .slice(0, 200);
        },
        activeCreateTimezoneSuggestionId() {
          if (
            !this.showTimezoneSuggestions
            || this.activeTimezoneSuggestionIndex < 0
            || this.activeTimezoneSuggestionIndex >= this.filteredTimezoneOptions.length
          ) {
            return "";
          }
          return this.timezoneSuggestionOptionId("create", this.activeTimezoneSuggestionIndex);
        },
        activeEditTimezoneSuggestionId() {
          if (
            !this.showEditTimezoneSuggestions
            || this.activeEditTimezoneSuggestionIndex < 0
            || this.activeEditTimezoneSuggestionIndex >= this.filteredEditTimezoneOptions.length
          ) {
            return "";
          }
          return this.timezoneSuggestionOptionId("edit", this.activeEditTimezoneSuggestionIndex);
        },
        activeCalendarTimezoneSuggestionId() {
          if (
            !this.showCalendarTimezoneSuggestions
            || this.activeCalendarTimezoneSuggestionIndex < 0
            || this.activeCalendarTimezoneSuggestionIndex >= this.filteredCalendarTimezoneOptions.length
          ) {
            return "";
          }
          return this.timezoneSuggestionOptionId("calendar", this.activeCalendarTimezoneSuggestionIndex);
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
      methods: {
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
            element.focus();
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
        focusAuthSuccessTarget(returnFocusTarget, options = {}) {
          this.$nextTick(() => {
            if (this.focusElementIfPossible(returnFocusTarget)) {
              return;
            }
            const sectionHeadingById = {
              list: "poll-list-heading",
              create: "create-poll-heading",
              selected: "details-heading",
              profile: "profile-heading"
            };
            const focusSectionHeading = () => this.focusElementById(
              sectionHeadingById[this.activeSection] || "poll-list-heading"
            );
            const focusTopbarTarget = () => {
              const topbarTarget = document.querySelector(".auth-actions .auth-name-link, .auth-actions .secondary");
              return this.focusElementIfPossible(topbarTarget);
            };

            if (options.preferSectionTarget) {
              if (!focusSectionHeading()) {
                focusTopbarTarget();
              }
              return;
            }

            if (!focusTopbarTarget()) {
              focusSectionHeading();
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
        timezoneSuggestionOptions(scope = "create") {
          if (scope === "calendar") {
            return this.filteredCalendarTimezoneOptions;
          }
          if (scope === "edit") {
            return this.filteredEditTimezoneOptions;
          }
          return this.filteredTimezoneOptions;
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
          const rawValue = scope === "calendar"
            ? this.calendarCustomTimezone
            : scope === "edit"
              ? (this.editForm ? this.editForm.timezone : "")
              : this.createForm.timezone;
          const normalizedValue = String(rawValue || "").trim().toLowerCase();
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
        bulkMenuStatuses() {
          return ["", "yes", "no", "maybe"];
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
            if (section === "create" && !options.skipFocus) {
              this.focusPollFormInitialField("create");
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
        pollOptionHasVotes(option) {
          return optionHasVotes(option);
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
        voteValueForOption(option) {
          if (!option) {
            return "";
          }
          return this.voteDraft[option.id] || "";
        },
        voteCellClass(option) {
          if (!option || typeof option !== "object") {
            return "vote-none";
          }
          if (this.voteDisplayMode === "own") {
            const ownValue = this.voteValueForOption(option);
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
        isSelectedVoteValue(option, status) {
          return this.voteValueForOption(option) === status;
        },
        optionCount(option, status) {
          return readOptionCount(option, status);
        },
        voteOptionAccessibleLabel(option, status) {
          const label = this.voteStatusLabel(status);
          const count = this.optionCount(option, status);
          return Number.isFinite(count) ? `${label} ${count}` : label;
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
        isVoteSaving(optionId) {
          return Boolean(this.savingVoteOptionIds[optionId]);
        },
        closeVoteMenus(options = {}) {
          const activeMenu = this.bulkMenu;
          this.bulkMenu = null;
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
        voteStatusOrder() {
          return ["yes", "maybe", "no"];
        },
        voteButtonTabIndex(option, status) {
          if (!option || !Number.isInteger(option.id)) {
            return -1;
          }
          const selected = this.voteValueForOption(option);
          if (selected) {
            return selected === status ? 0 : -1;
          }
          return status === "yes" ? 0 : -1;
        },
        focusVoteButton(optionId, status) {
          const selector = `.vote-switch-option[data-vote-option-id="${optionId}"][data-vote-status="${status}"]`;
          const button = document.querySelector(selector);
          if (button && typeof button.focus === "function") {
            button.focus();
          }
        },
        async handleVoteSwitchKeydown(event, option, status) {
          if (
            !option
            || !Number.isInteger(option.id)
            || !this.canVoteInPoll
            || this.isVoteSaving(option.id)
          ) {
            return;
          }
          const order = this.voteStatusOrder();
          const currentIndex = order.indexOf(status);
          let nextStatus = "";
          if (event.key === "ArrowRight" || event.key === "ArrowDown") {
            nextStatus = order[(currentIndex + 1) % order.length];
          } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
            nextStatus = order[(currentIndex - 1 + order.length) % order.length];
          } else if (event.key === "Home") {
            nextStatus = order[0];
          } else if (event.key === "End") {
            nextStatus = order[order.length - 1];
          } else {
            return;
          }
          event.preventDefault();
          await this.setVoteStatus(option, nextStatus);
          this.$nextTick(() => {
            this.focusVoteButton(option.id, nextStatus);
          });
        },
        async setVoteStatus(option, status) {
          if (!option || !Number.isInteger(option.id)) {
            return;
          }
          if (!this.isVoteStatus(status)) {
            return;
          }
          if (!this.canVoteInPoll || this.isVoteSaving(option.id)) {
            return;
          }
          const currentStatus = this.voteValueForOption(option);
          const nextStatus = nextVoteStatus(currentStatus, status);
          this.closeVoteMenus();
          await this.applyVotes([option.id], nextStatus);
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

            if (uniqueOptionIds.some((optionId) => this.isVoteSaving(optionId))) {
              return;
            }

            const idSet = new Set(uniqueOptionIds);
            const targetOptions = this.selectedPoll.options.filter((item) => idSet.has(item.id));
            if (!targetOptions.length) {
              return;
            }

            const changedOptions = [];
            for (const option of targetOptions) {
              const previousStatus = this.voteDraft[option.id] || "";
              if (previousStatus === normalizedStatus) {
                continue;
              }

              const previousCounts = {
                yes: Number((option.counts && option.counts.yes) || 0),
                no: Number((option.counts && option.counts.no) || 0),
                maybe: Number((option.counts && option.counts.maybe) || 0)
              };
              const previousMyVote = option.my_vote || null;

              if (!option.counts) {
                option.counts = { yes: 0, no: 0, maybe: 0 };
              }

              if (this.isVoteStatus(previousStatus) && option.counts[previousStatus] > 0) {
                option.counts[previousStatus] -= 1;
              }
              if (this.isVoteStatus(normalizedStatus)) {
                option.counts[normalizedStatus] = Number(option.counts[normalizedStatus] || 0) + 1;
                option.my_vote = normalizedStatus;
              } else {
                option.my_vote = null;
              }

              this.voteDraft[option.id] = normalizedStatus;
              changedOptions.push({
                optionId: option.id,
                previousStatus,
                previousCounts,
                previousMyVote
              });
            }

            if (!changedOptions.length) {
              return;
            }

            for (const change of changedOptions) {
              this.savingVoteOptionIds[change.optionId] = true;
            }

            try {
              const data = await apiFetch(`/api/polls/${this.selectedPoll.id}/votes/`, {
                method: "PUT",
                body: {
                  votes: changedOptions.map((change) => ({
                    option_id: change.optionId,
                    status: normalizedStatus || null
                  }))
                }
              });
              this.selectedPoll = data.poll;
              this.applyVoteDraft();
              await this.fetchPolls();
            } catch (error) {
              for (const change of changedOptions) {
                const option = this.selectedPoll.options.find((item) => item.id === change.optionId);
                if (option) {
                  option.counts = {
                    yes: change.previousCounts.yes,
                    no: change.previousCounts.no,
                    maybe: change.previousCounts.maybe
                  };
                  option.my_vote = change.previousMyVote;
                }
                this.voteDraft[change.optionId] = change.previousStatus;
              }
              this.setError(this.resolveError(error.payload, "Could not save vote."));
            } finally {
              for (const change of changedOptions) {
                delete this.savingVoteOptionIds[change.optionId];
              }
            }
          });
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
        },
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
          this.setActiveSection("profile");
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
        },
        async fetchPolls() {
          try {
            const data = await apiFetch("/api/polls/");
            this.polls = data.polls || [];
          } catch (error) {
            this.setError(this.resolveError(error.payload, "Could not load polls."));
          }
        },
        applyVoteDraft() {
          const draft = {};
          if (!this.selectedPoll) {
            this.voteDraft = draft;
            this.closeVoteMenus();
            return;
          }
          for (const option of this.selectedPoll.options) {
            if (option.my_vote === "yes" || option.my_vote === "no" || option.my_vote === "maybe") {
              draft[option.id] = option.my_vote;
            } else {
              draft[option.id] = "";
            }
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
            this.setActiveSection("selected", { skipUrlSync: true });
            this.applyVoteDraft();
            if (options.syncUrl !== false) {
              this.setPollIdInCurrentUrl(this.selectedPoll.id, {
                replace: Boolean(options.replaceUrl)
              });
            }
          } catch (error) {
            this.setError(this.resolveError(error.payload, "Could not open poll."));
            if (options.fromUrl) {
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
              await this.openPoll(data.poll.id, { preserveFeedback: true });
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
              await apiFetch(`/api/polls/${this.selectedPoll.id}/`, { method: "DELETE" });
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
      },
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
        });
      },
      beforeUnmount() {
        this.clearSuccessFeedbackTimer();
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
