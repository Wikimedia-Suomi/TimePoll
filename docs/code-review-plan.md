# Code Review -suunnitelma

Tämä dokumentti määrittelee toistettavan code review -mallin TimePoll-projektille.

Tavoite ei ole tehdä yhtä geneeristä "katso vähän kaikkea" -kierrosta, vaan vaiheistettu review, joka voidaan toistaa myöhemmin samalla rungolla ja samalla painotuksella.

Suunnitelma on tarkoitettu erityisesti näihin teemoihin:

- tietoturva paikallisen kehityksen, palvelinpään ja käyttäjän kannalta
- refaktoroinneista jäänyt käyttämätön tai vain sisäisen taaksepäinyhteensopivuuden vuoksi elävä koodi
- koodin laatu yleisesti
- koodin ymmärrettävyys yleisesti
- ohjelman yleinen saavutettavuus eri päätelaitteilla
- muut merkittävät riskit, joita ei kannata jättää review’n ulkopuolelle

## Periaatteet

Review tehdään vaiheissa. Kaikkea ei arvioida yhdellä kertaa, koska codebasessa on muutama hyvin suuri keskittymä:

- `polls/static/polls/js/app.js`
- `polls/views.py`
- `polls/templates/polls/index.html`
- `timepoll/runtime_guard.py`
- isot backend-, browser- ja storyboard-testit

Review’n aikana pidetään nämä periaatteet:

- löydökset raportoidaan vakavuusjärjestyksessä
- erotellaan todetut löydökset, epävarmat havainnot ja jatkotarkistusta vaativat kohdat
- workflow- ja käytettävyysongelmat käsitellään yhtä vakavasti kuin mekaaniset virheet silloin, kun ne vaikuttavat oikeaan käyttöön
- review voidaan tehdä osissa
- review’n tavoitteena ei ole automaattisesti muuttaa koodia, vaan ensin ymmärtää nykytila

## Vakavuusluokat

Suositeltu luokittelu:

- `Korkea`: turvallisuus-, datan eheys-, käyttökatko- tai merkittävä saavutettavuus/workflow-riski
- `Keskitaso`: selvä ylläpidettävyys-, laatu- tai käytettävyysongelma, joka ei yleensä aiheuta välitöntä kriittistä virhettä
- `Matala`: siivous, johdonmukaisuus, nimeäminen, dokumentointi tai muu pienempi parannuskohde

## Review’n tuotokset

Jokaisesta vaiheesta pitäisi syntyä vähintään:

- lista löydöksistä vakavuusjärjestyksessä
- lista avoimista kysymyksistä tai oletuksista
- lista nopeista korjauksista
- lista isommista rakenneparannuksista, joita ei kannata tehdä kiireessä

Hyvä lopputulos on sellainen, jossa voidaan erottaa:

- asiat jotka pitäisi korjata heti
- asiat jotka kannattaa siirtää backlogiin
- asiat jotka ovat tietoisia tradeoffeja eikä varsinaisia virheitä

## Suositeltu suoritusjärjestys

Review kannattaa tehdä tässä järjestyksessä:

1. tietoturva ja riippuvuudet
2. refaktorointijäämät ja käyttämätön koodi
3. koodin laatu ja ymmärrettävyys
4. saavutettavuus ja päätelaitteet
5. muut poikkileikkaavat riskit

Tätä järjestystä kannattaa noudattaa erityisesti silloin, kun review tehdään ajan kanssa useassa osassa.

## Vaihe 1: Tietoturva ja riippuvuudet

Ensimmäinen review-kierros kohdistuu siihen, onko järjestelmässä turvallisuusriskejä:

- paikallisen kehityksen näkökulmasta
- palvelinpuolen näkökulmasta
- käyttäjän näkökulmasta

### Kysymykset

- Onko kehitysympäristön oletuksissa jotain vaarallista tai helposti väärin käytettävää?
- Onko palvelinpuolen endpointtien oikeuksissa, validoinnissa tai virhepalautteissa aukkoja?
- Onko autentikointi ja sessioiden käyttö riittävän turvallista tähän käyttötapaukseen?
- Onko poll-linkkien, tunnisteiden tai käyttäjätietojen käsittelyssä arvattavuus- tai tietovuotoriskejä?
- Onko CSP, CDN-riippuvuus tai runtime guard rakennettu johdonmukaisesti?
- Onko kehitystyökalujen tai riippuvuuksien kautta jäänyt tunnettuja riskejä?

### Pääkohteet

- `timepoll/settings.py`
- `timepoll/security.py`
- `timepoll/runtime_guard.py`
- `polls/views.py`
- `polls/models.py`
- `requirements.txt`
- `requirements-dev.txt`
- `README.md`
- `Makefile`
- `tools/security.sh`
- `tools/audit.sh`

### Tarkistuslista

- ympäristömuuttujien pakollisuus ja oletukset
- `DEBUG`, `ALLOWED_HOSTS`, secretit, cookie-asetukset
- CSRF-käytös
- autentikointi ja sessionhallinta
- oikeustarkastukset API-kutsuissa
- input-validointi ja virheilmoitukset
- CSP ja ulkoiset skriptit
- `pip-audit`-löydökset ja ignorat
- runtime guardin enforce/log/off -polut
- kehitysympäristön writable-polut ja subprocess-/network-guardit

### Tuotos

- erillinen lista:
  - paikallisen kehityksen riskit
  - palvelinpuolen riskit
  - käyttäjän näkökulman riskit

## Vaihe 2: Refaktorointijäämät ja käyttämätön koodi

Tämän vaiheen tarkoitus on löytää koodi, joka on jäänyt elämään refaktoroinneista:

- ilman nykyisiä kutsupaikkoja
- vanhan toteutuksen nimillä
- vain sisäisen taaksepäinyhteensopivuuden vuoksi
- testien tai dokumentaation kautta, vaikka runtime ei enää käytä sitä

### Kysymykset

- Onko helper-funktioita, state-kenttiä tai template-haaroja joita ei enää käytetä?
- Onko vanhoja nimiä, jotka hämärtävät nykyistä mallia?
- Onko testejä, fixturejä tai dokumentaatiota, jotka puhuvat vanhasta toteutuksesta?
- Onko backendissä tai frontendissä polkuja, joita ylläpidetään vain historiallisista syistä?

### Pääkohteet

- `polls/static/polls/js/app.js`
- `polls/static/polls/js/app_logic.js`
- `polls/templates/polls/index.html`
- `polls/views.py`
- `polls/tests.py`
- `polls/tests_browser.py`
- `polls/tests_browser_storyboard.py`

### Tarkistuslista

- käyttämättömät helperit
- käyttämättömät state-polut
- vanhat CSS-luokat tai DOM-rakenteet
- vanhentuneet testinimet
- vanhentuneet kommentit
- vanhat API-muodot, joita nykyinen UI ei enää käytä
- sisäinen backward compatibility, jolle ei ole enää todellista tarvetta

### Menetelmä

- käytä tekstihakua ja callsite-tarkistusta
- vertaa templatea, JS-logiikkaa ja testejä keskenään
- tarkista löytyykö "ghost code" -tyyppisiä polkuja, joita vain yksi vanha testi enää käyttää

### Tuotos

- lista koodista, joka voidaan poistaa suoraan
- lista koodista, joka vaatii ensin vahvistuksen ennen poistoa
- lista nimistä ja käsitteistä, jotka pitäisi päivittää vastaamaan nykytilaa

## Vaihe 3: Koodin laatu ja ymmärrettävyys

Tässä vaiheessa arvioidaan, kuinka helposti koodia voi ylläpitää ja ymmärtää.

### Kysymykset

- Onko koodissa liian suuria tiedostoja tai funktioita?
- Onko logiikka hajallaan useassa paikassa niin, että muutokset ovat riskialttiita?
- Onko backendin ja frontendin välinen data contract helposti ymmärrettävä?
- Onko testit rakennettu tukemaan turvallista refaktorointia?
- Onko nimeäminen, vastuunjako ja rakenne johdonmukaista?

### Pääkohteet

- `polls/views.py`
- `polls/static/polls/js/app.js`
- `polls/static/polls/js/app_logic.js`
- `timepoll/runtime_guard.py`
- `polls/templates/polls/index.html`

### Tarkistuslista

- liian pitkät funktiot
- liian laajat komponentti-/view-state-rakenteet
- duplikoitu validaatio
- epäselvät vastuurajat
- epäjohdonmukaiset virhepolut
- vaikeasti testattavat sivuvaikutukset
- kommenttien ja nimeämisen laatu
- puuttuuko täsmädokumentointia kriittisistä workflow’ista

### Tuotos

- lista "quick refactor" -kohteista
- lista laajemmista rakenneparannuksista
- lista kohdista, joihin kannattaa lisätä dokumentaatiota tai täsmäkommentteja

## Vaihe 4: Saavutettavuus ja päätelaitteet

Tämän vaiheen painopiste ei ole vain mekaaninen WCAG-tarkastus, vaan se, onko käyttöliittymä oikeasti toimiva:

- näppäimistöllä
- ruudunlukijalla
- mobiilissa
- eri selaimilla ja eri päätelaitteilla

### Kysymykset

- Toimivatko pääworkflow’t ilman hiirtä?
- Liikkuuko fokus oikein näkymästä toiseen?
- Toimivatko dialogit, lomakkeet ja kalenteri eri käyttötilanteissa?
- Onko Safari/macOS-käyttäytyminen dokumentoitu ja huomioitu?
- Onko ruudunlukijakäyttö toimiva eikä vain semanttisesti "sinne päin"?

### Pääkohteet

- `polls/templates/polls/index.html`
- `polls/static/polls/js/app.js`
- `polls/static/polls/css/app.css`
- `polls/tests_browser.py`
- `polls/tests_browser_storyboard.py`
- `docs/accessibility.md`

### Tarkistuslista

- fokusjärjestys
- paluupolut
- dialogien fokuslukitus ja palautus
- lomakkeiden virhetilat
- kalenterin keyboard-workflow
- ruudunlukijan ilmoitukset
- pienet viewportit ja mobiiliasettelu
- Safari/macOS-erikoiskäytös
- axe-testien kattavuus vs manuaalisen testauksen tarve

### Tuotos

- mekaaniset saavutettavuuslöydökset
- workflow-löydökset
- päätelaite- tai selainkohtaiset caveatit

## Vaihe 5: Muut poikkileikkaavat riskit

Vaikka ne eivät olisi review’n pääteemoja, nämä kannattaa tarkistaa lopuksi:

- suorituskyky
- timezone- ja päivämäärälogiikan oikeellisuus
- i18n/l10n-konsistenssi
- testien flakeys
- operoitavuus ja diagnosoitavuus
- dokumentaation ajantasaisuus

### Kysymykset

- Skaalautuuko iso polli tai tiheä kalenteri järkevästi?
- Onko DST- ja timezone-logiikassa vaikeasti havaittavia reunatapauksia?
- Ovatko käännökset, labelit ja virheilmoitukset yhtenäisiä?
- Onko testisuite luotettava vai sisältääkö paljon satunnaisesti rikkoutuvia odotuksia?
- Löytyykö käyttäytymisestä jotain, mitä nykyinen dokumentaatio ei kerro?

### Tuotos

- lista riskeistä, jotka eivät kuulu puhtaasti turvallisuuteen, laatuun tai saavutettavuuteen mutta vaikuttavat ylläpitoon

## Käytännön toteutustapa

Suositeltu toistettava rytmi:

1. tee ensin rajaus: mikä vaihe review’sta tehdään tällä kierroksella
2. lue ensin keskeiset tiedostot ilman muutoksia
3. tee havainnot vakavuusjärjestyksessä
4. vahvista epävarmat kohdat kohdennetuilla hauilla ja testeillä
5. erottele selvästi:
   - todetut löydökset
   - avoimet kysymykset
   - suositellut jatkotoimet

## Suositellut peruskomennot

Review’n aikana hyödyllisiä peruskomentoja:

```bash
rg --files
rg -n "hakusana" polls timepoll docs tools
sh tools/lint.sh
sh tools/typecheck.sh
sh tools/test-backend.sh
sh tools/test-browser.sh
sh tools/test-browser-storyboard.sh
sh tools/pre-push.sh
```

Kaikkia testejä ei tarvitse ajaa jokaisessa review-vaiheessa. Kohdennetut ajot ovat yleensä tehokkaampia.

## Suositeltu raportointimuoto

Jokainen review-raportti kannattaa jäsentää näin:

### Löydökset

- vakavin ensin
- tiedosto- ja tarvittaessa riviviitteet mukana

### Avoimet kysymykset

- asiat joita ei voitu varmistaa ilman lisätietoa tai manuaalitestausta

### Yhteenveto

- lyhyt arvio kokonaisriskistä
- mitä kannattaa tehdä seuraavaksi

## Milloin review kannattaa pilkkoa osiin

Review kannattaa tehdä erissä ainakin silloin, kun:

- halutaan ensin turvallisuusarvio ennen muita muutoksia
- frontendin saavutettavuustyö on kesken
- refaktoroinnin jälkeen halutaan ensin siivota jäljelle jäänyt legacy-koodi
- testisuite on muuttunut ja sen luotettavuutta pitää arvioida erikseen

## TimePoll-kohtainen suositus

Tässä repossa hyvä oletus on tehdä review neljänä eränä:

1. tietoturva ja riippuvuudet
2. refaktorointijäämät ja kuollut koodi
3. koodin laatu ja ymmärrettävyys
4. saavutettavuus ja päätelaitteet

Tätä mallia kannattaa käyttää myös jatkossa, jotta eri review-kierrokset ovat vertailukelpoisia keskenään.
