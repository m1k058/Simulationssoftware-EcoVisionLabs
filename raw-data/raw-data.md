# Raw Input Datein

Hier eine zusammenfassung aller Daten die als Basis für das Simulationsprogramm eingebaut sind.
- Realisierte Erzeugung von **SMARD**
- Realisierter Verbrauch von **SMARD**
- Instaliere Leistung von **SMARD**
- Prognosedaten aus Studien vom **DV-Team** zusammengefasst
- Lastprofile vom **BDEW** in einzelne `.csv` aufgeteilt vom **SW-Team**

| ID | Dateiname | Beschreibung | Zeitliche Auflösung | Dateiformat | Datentyp | Herkunft |
|---|---|---|---|---|---|---|
|0| Realisierte_Erzeugung_2015-2019 |SMARD_2015-2019_Erzeugung|Viertelstündig (Orginalauflösung)|`.csv`|`SMARD`|smard.de|
|1| Realisierte_Erzeugung_2020-2025 |SMARD_2020-2025_Erzeugung|Viertelstündig (Orginalauflösung)|`.csv`|`SMARD`|smard.de|
|2| Realisierter_Stromverbrauch_2015-2019 |SMARD_2015-2019_Verbrauch|Viertelstündig (Orginalauflösung)|`.csv`|`SMARD-V`|smard.de|
|3| Realisierter_Stromverbrauch_2020-2025 |SMARD_2020-2025_Verbrauch|Viertelstündig (Orginalauflösung)|`.csv`|`SMARD-V`|smard.de|
|4| Instalierte_Leistung_2015-2019 |SMARD_Installierte Leistung 2015-2019|Viertelstündig (Orginalauflösung)| `.csv` |`SMARD-Inst`|smard.de|
|5| Instalierte_Leistung_2020-2025 |SMARD_Installierte Leistung 2020-2025|Viertelstündig (Orginalauflösung)| `.csv` |`SMARD-Inst`|smard.de|
|6| Prognosedaten_Studien |Erzeugungs- und Verbrauchsprognosen verschiedener Studien|Jahreswerte (ausgewählt)|`.csv`|`CUST_PROG`|DV-Team|
|7|BDEW-Standardlastprofile-H25|Verbrauchsprofil Haushalte BDEW|Viertelstündig|`.csv`|`BDEW-Last`|bdew.de (SW-Team)|
|8|BDEW-Standardlastprofile-G25|Verbrauchsprofil Gewerbe BDEW|Viertelstündig|`.csv`|`BDEW-Last`|bdew.de (SW-Team)|
|9|BDEW-Standardlastprofile-L25|Verbrauchsprofil Landwirtshaft BDEW|Viertelstündig|`.csv`|`BDEW-Last`|bdew.de (SW-Team)|
