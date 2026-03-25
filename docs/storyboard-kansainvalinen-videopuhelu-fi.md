# Storyboard: Yhteisen videopuheluajan sopiminen neljälle käyttäjälle

## Tilanne

Neljä käyttäjää yrittää löytää yhteisen 60 minuutin videopuheluajan seuraavalle viikolle, eli ajalle 30.3.2026-5.4.2026.

- Aino, Helsinki (`Europe/Helsinki`) toimii kyselyn aloittajana.
- Maya, New York (`America/New_York`) osallistuu Yhdysvalloista.
- Kenji, Tokio (`Asia/Tokyo`) osallistuu Japanista.
- Leila, Nairobi (`Africa/Nairobi`) vastaa käyttäen näppäimistöä ja ruudunlukijaa.

Tavoite on löytää yksi aika, joka sopii kaikille neljälle. Storyboard päättyy siihen, että Aino sulkee kyselyn ja poistaa sen.

## Storyboardissa käytettävät ominaisuudet

- kirjautuminen nimellä ja PIN-koodilla
- käyttöliittymän kielen vaihto
- kyselyn luonti otsikolla, kuvauksella ja omalla tunnisteella
- aikavyöhykkeen valinta ehdotuslistasta
- viikonpäivien ja päivittäisen aikaikkunan rajaus
- kyselyn muokkaus ennen jakamista
- kyselylinkin avaaminen tunnisteen perusteella
- omien äänten antaminen `Kyllä`, `Ehkä`, `Ei` ja tarvittaessa äänen poistaminen
- sarake- ja rivikohtainen bulk-äänestys
- kalenterin tarkastelu kyselyn aikavyöhykkeellä, selaimen aikavyöhykkeellä ja omalla mukautetulla aikavyöhykkeellä
- näppäimistökäyttöinen ja ruudunlukijalla hahmotettava äänestäminen
- tulostila ja `Kyllä`-äänisuodatin
- profiilin käyttö omien äänten tarkasteluun ja yksittäisen äänen poistoon
- kyselyn sulkeminen ja poistaminen

## Askel askeleelta

### Vaihe 1: Aino luo kyselyn

1. Aino avaa TimePollin etusivun Helsingissä.
2. Hän vaihtaa yläpalkin kielivalitsimesta käyttöliittymän kieleksi suomen.
3. Aino painaa `Kirjaudu`.
4. Hän syöttää nimeksi `Aino` ja PIN-koodiksi `4826`.
5. Koska käyttäjää ei ole vielä olemassa, järjestelmä luo Ainolle uuden käyttäjän ja kirjaa hänet sisään.
6. Aino näkee kyselylistan ja painaa `Luo uusi kysely`.
7. Hän täyttää otsikoksi `Maailmanlaajuinen tiimipuhelu`.
8. Hän kirjoittaa kuvaukseen: `Sovitaan ensi viikon videopuhelu. Valitse kaikki ajat, jotka sopivat varmasti tai ehkä.`
9. Hän kirjoittaa kyselyn tunnisteeksi `global_video_sync`.
10. Aino siirtyy aikavyöhykekenttään ja kirjoittaa pienillä kirjaimilla `europe/hel`.
11. Järjestelmä näyttää aikavyöhyke-ehdotukset.
12. Aino valitsee listasta `Europe/Helsinki`.
13. Hän asettaa alkupäiväksi `2026-03-30`.
14. Hän asettaa loppupäiväksi `2026-04-05`.
15. Hän valitsee päivittäiseksi aloitusajaksi `15:00`.
16. Hän valitsee päivittäiseksi lopetusajaksi `20:00`.
17. Hän jättää viikonpäivistä valituiksi maanantain, tiistain, keskiviikon, torstain ja perjantain.
18. Hän poistaa valinnat lauantaista ja sunnuntaista, jotta viikonloppu ei näy kyselyssä.
19. Aino painaa `Luo kysely`.
20. Järjestelmä luo automaattisesti tuntislotit valituille arkipäiville ja avaa kyselyn yksityiskohtanäkymän.
21. Osoiteriville muodostuu tunnisteellinen linkki, jonka lopussa on `?id=global_video_sync`.

### Vaihe 2: Aino tarkentaa kyselyä ennen jakamista

22. Aino huomaa, että viimeinen mahdollinen aika voisi ulottua vielä tunnin myöhemmäksi.
23. Hän painaa `Muokkaa kyselyä`.
24. Hän muuttaa kuvauksen muotoon: `Sovitaan ensi viikon videopuhelu. Merkitse kaikki varmasti sopivat ajat Kyllä-vastauksella ja epävarmat Ehkä-vastauksella.`
25. Hän muuttaa päivittäiseksi lopetusajaksi `21:00`.
26. Hän tarkistaa, että aikavyöhyke on yhä `Europe/Helsinki` ja että tunniste on edelleen `global_video_sync`.
27. Hän painaa `Tallenna muutokset`.
28. Järjestelmä päivittää kyselyn ja näyttää onnistumisviestin.

### Vaihe 3: Aino antaa omat vastauksensa

29. Aino pysyy kyselyn näkymässä ja alkaa merkitä omia sopivia aikojaan.
30. Hän avaa torstain 2.4.2026 päivän otsikosta päivän bulk-valikon.
31. Hän valitsee bulk-valikosta `Ehkä`, jolloin kaikki torstain näkyvät slotit merkitään ensin alustavasti mahdollisiksi.
32. Sen jälkeen hän avaa rivin `16:00` bulk-valikon.
33. Hän valitsee riville `Kyllä`, jolloin kaikkien näkyvien päivien klo 16.00 slotit muuttuvat `Kyllä`-tilaan.
34. Aino tarkentaa vastauksia yksittäisissä soluissa.
35. Hän klikkaa torstain 2.4.2026 klo 16.00 solussa `Kyllä`, jotta juuri tämä slot pysyy varmasti mukana.
36. Hän klikkaa maanantain 30.3.2026 klo 16.00 solussa `Ei`, koska silloin hänellä on toinen kokous.
37. Hän klikkaa torstain 2.4.2026 klo 18.00 solussa `Ehkä` toisen kerran poistaakseen siitä alustavan äänen kokonaan.
38. Nyt Ainon tärkein toive on torstai 2.4.2026 klo 16.00 Helsingin aikaa.

### Vaihe 4: Aino jakaa kyselyn

39. Aino kopioi selaimen osoiteriviltä linkin, jossa on tunniste `global_video_sync`.
40. Hän lähettää saman linkin Mayalle, Kenjille ja Leilalle viestisovelluksessa.
41. Viestissä hän kertoo, että tavoite on löytää yhteinen videopuheluaika viikolle 30.3.2026-5.4.2026.

### Vaihe 5: Maya avaa kyselyn ja vastaa New Yorkista

42. Maya avaa saamansa linkin New Yorkissa.
43. Kysely avautuu suoraan valittuun näkymään linkin tunnisteen perusteella ilman, että hänen täytyy etsiä sitä listasta.
44. Maya vaihtaa käyttöliittymän kieleksi englannin.
45. Hän painaa `Login`.
46. Hän syöttää nimeksi `Maya` ja PIN-koodiksi `9035`.
47. Järjestelmä luo Mayalle käyttäjän ja kirjaa hänet sisään.
48. Maya huomaa, että kalenteri näyttää oletuksena kyselyn aikavyöhykkeen eli Helsingin ajat.
49. Hän vaihtaa kalenterin aikavyöhyketilaksi `Browser timezone`.
50. Kalenterin ajat päivittyvät New Yorkin paikalliseen aikaan.
51. Maya näkee, että torstai 2.4.2026 klo 16.00 Helsingissä vastaa New Yorkissa torstaita 2.4.2026 klo 09.00.
52. Maya pitää 09.00 aikaa hyvänä ja merkitsee kyseisen solun `Yes`.
53. Hän avaa rivin `10:00` bulk-valikon omassa paikallisessa näkymässään.
54. Hän valitsee `Maybe`, jolloin kaikki näkyvät päivät klo 10.00 merkitään alustavasti mahdollisiksi.
55. Maya huomaa, että keskiviikon 1.4.2026 klo 10.00 ei sovikaan hänelle.
56. Hän avaa kyseisen yksittäisen solun ja vaihtaa sen tilaan `No`.
57. Hän huomaa torstain 2.4.2026 klo 11.00 olevan myös mahdollinen ja klikkaa sille `Maybe`.

### Vaihe 6: Maya tarkistaa profiilinsa ja korjaa yhden äänen

58. Maya haluaa tarkistaa, mitä hän on jo äänestänyt.
59. Hän painaa yläpalkista omaa nimeään, jolloin `My data` -näkymä avautuu.
60. Profiilin `My votes` -listassa hän näkee kyselyn `Maailmanlaajuinen tiimipuhelu` ja omat vastauksensa.
61. Hän huomaa merkinneensä yhden slotin liian optimistisesti.
62. Maya painaa kyseisen rivin `Delete vote` -painiketta.
63. Järjestelmä poistaa juuri sen yhden äänen ja päivittää profiilin listan.
64. Maya painaa profiilista `Open poll`, jolloin sama kysely avautuu takaisin yksityiskohtanäkymään.
65. Hän lisää korvaavan äänen torstain 2.4.2026 klo 09.00 slotille, joka vastaa Helsingin aikaa klo 16.00.

### Vaihe 7: Kenji avaa kyselyn ja käyttää omaa aikavyöhykettä

66. Kenji avaa Ainon lähettämän linkin Tokiossa.
67. Hän pitää käyttöliittymän englanniksi.
68. Hän painaa `Login`.
69. Hän syöttää nimeksi `Kenji` ja PIN-koodiksi `1174`.
70. Järjestelmä luo Kenjille käyttäjän ja kirjaa hänet sisään.
71. Kenji haluaa nähdä kalenterin nimenomaan omassa aikavyöhykkeessään.
72. Hän valitsee kalenterin aikavyöhdetilaksi `Own timezone`.
73. Mukautettu aikavyöhykekenttä avautuu.
74. Kenji kirjoittaa kenttään `asia/tok`.
75. Järjestelmä näyttää aikavyöhyke-ehdotukset.
76. Kenji valitsee listasta `Asia/Tokyo`.
77. Kalenterin ajat päivittyvät Tokion paikalliseen aikaan.
78. Hän näkee, että torstai 2.4.2026 klo 16.00 Helsingissä vastaa Tokiossa torstaita 2.4.2026 klo 22.00.
79. Kenji avaa torstain sarakekohtaisen bulk-valikon.
80. Hän valitsee `No`, koska suuri osa torstain myöhäisillasta ei sovi hänelle.
81. Tämän jälkeen hän tarkentaa yksittäisiä poikkeuksia.
82. Hän klikkaa torstain 2.4.2026 klo 22.00 solun `Yes`, koska juuri se aika sopii hänelle.
83. Hän klikkaa torstain 2.4.2026 klo 23.00 solun `Maybe`, koska se olisi mahdollinen varavaihtoehto.
84. Hän jättää muut torstain slotit `No`-tilaan.

### Vaihe 8: Leila avaa kyselyn näppäimistöllä ja ruudunlukijalla

85. Leila avaa Ainon lähettämän linkin Nairobissa.
86. Hän käyttää vain näppäimistöä ja ruudunlukijaa, ei hiirtä.
87. Ruudunlukija lukee sivun otsikon ja ensimmäiset navigoitavat ohjaimet.
88. Leila siirtyy `Tab`-näppäimellä `Login`-painikkeeseen ja painaa `Enter`.
89. Kirjautumisikkuna avautuu, ja ruudunlukija ilmoittaa otsikon `Login` sekä kentät `Name` ja `PIN`.
90. Leila kirjoittaa nimeksi `Leila` ja PIN-koodiksi `5512`.
91. Hän lähettää kirjautumisen painamalla `Enter`.
92. Järjestelmä luo Leilalle uuden käyttäjän ja kirjaa hänet sisään.
93. Leila kuuntelee kyselyn otsikon ja kuvauksen ruudunlukijalla varmistaakseen, että hän on oikeassa kyselyssä.
94. Hän siirtyy `Tab`-näppäimellä torstain 2.4.2026 sarakeotsikon bulk-painikkeeseen.
95. Ruudunlukija lukee torstain otsikon painikkeena.
96. Leila painaa `Enter`, jolloin päivän bulk-menu avautuu ja kohdistus siirtyy valikon ensimmäiseen kohtaan.
97. Hän painaa `Nuoli alas` kolme kertaa siirtyäkseen kohtaan `Maybe`.
98. Hän painaa `Enter`, jolloin torstain näkyvät slotit merkitään ensin `Maybe`-tilaan.
99. Leila siirtyy `Tab`-näppäimellä torstain 2.4.2026 klo 16.00 ääniryhmään.
100. Ruudunlukija ilmoittaa ryhmän nimellä, joka sisältää päivän ja kellonajan.
101. Koska slotin tila on tällä hetkellä `Maybe`, kohdistus on `Maybe`-radiopainikkeessa.
102. Leila painaa `Nuoli vasen`, jolloin valinta siirtyy `Yes`-tilaan.
103. Ruudunlukija ilmoittaa, että `Yes` on nyt valittu.
104. Leila siirtyy seuraavaan torstain slotiin, joka vastaa myöhempää ilta-aikaa.
105. Hän käyttää nuolinäppäimiä vaihtaakseen sen tilaan `No`, jotta liian myöhäinen vaihtoehto rajautuu pois.
106. Leila jättää torstain 2.4.2026 klo 16.00 Helsingin aikaa vastaavan slotin ainoaksi varmaksi `Yes`-valinnakseen.
107. Koska Nairobi ja Helsinki ovat tällä viikolla samassa UTC+3-aikavyöhykkeessä, Leila näkee saman slotin myös omassa paikallisessa ajassaan klo 16.00.

### Vaihe 9: Aino vertailee kaikkien vastauksia

108. Kun Aino saa viestin, että kaikki neljä ovat vastanneet, hän avaa kyselyn uudelleen Helsingissä.
109. Hän pitää kalenterin aikavyöhykkeenä kyselyn alkuperäisen aikavyöhykkeen eli `Europe/Helsinki`.
110. Hän vaihtaa ääninäyttötilaksi `Tulostila`, jotta ruudukossa korostuvat yhteiset tulokset eikä vain hänen oma äänensä.
111. Järjestelmä näyttää jokaisessa slotissa `Kyllä`, `Ehkä` ja `Ei` -äänien määrät.
112. Aino avaa `Kyllä`-äänisuodattimen.
113. Hän valitsee suodattimen arvoksi `4`.
114. Järjestelmä piilottaa kaikki rivit, joilla ei ole vähintään neljää `Kyllä`-ääntä.
115. Ruudukkoon jää näkyviin yksi selkeä vaihtoehto: torstai 2.4.2026 klo 16.00 Helsingin aikaa.
116. Aino toteaa, että sama aika tarkoittaa New Yorkissa klo 09.00, Tokiossa klo 22.00 ja Nairobissa klo 16.00.
117. Hän lähettää tämän lopputuloksen Mayalle, Kenjille ja Leilalle erillisellä viestillä.

### Vaihe 10: Aino sulkee kyselyn

118. Kun kaikki ovat hyväksyneet yhteisen ajan, Aino palaa TimePollin kyselynäkymään.
119. Hän painaa `Sulje kysely`.
120. Järjestelmä päivittää kyselyn tilaksi `Kysely on suljettu`.
121. Kyselyn äänestyspainikkeet eivät ole enää muokattavissa.
122. Suljettu tila kertoo selvästi, ettei vastauksia voi enää muuttaa vahingossa.

### Vaihe 11: Aino poistaa kyselyn

123. Kun videopuhelu on lisätty kaikkien kalentereihin, Aino siivoaa kyselylistan.
124. Hän painaa `Poista kysely`.
125. Selain näyttää vahvistuskysymyksen, jossa poistaminen pitää hyväksyä erikseen.
126. Aino vahvistaa poiston.
127. Järjestelmä poistaa kyselyn pysyvästi.
128. Käyttöliittymä palauttaa Ainon kyselylistaan.
129. Poistettu kysely ei enää näy listalla.

## Lopputulos

Aino loi kyselyn, muokkasi sitä ennen jakamista, vastasi siihen itse ja jakoi tunnisteellisen linkin kolmelle muulle osallistujalle. Maya, Kenji ja Leila vastasivat eri puolilta maailmaa käyttäen eri kalenterinäkymiä ja useita äänestystapoja. Leilan osuus näyttää erikseen, miten sama kysely toimii näppäimistöllä ja ruudunlukijalla. Lopuksi Aino käytti tulostilaa ja `Kyllä`-suodatinta yhteisen ajan löytämiseen, sulki kyselyn ja poisti sen hallitusti.
