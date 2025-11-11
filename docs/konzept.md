- E-Autos als Speicher?
- Marktanteil E-Autos
- Merit Order Prinzip
- Ausbau erneuerbare vs Menge an konventionellen
- Blackouts, Dunkelflauten
    - Speicherausbau, benötigte Reservekapazitäten
- Szenarien auswählen und Annahmen treffen
    - realistische und evtl unrealistische Szenarien
- Wirtschaftlichkeit vs. Klimaschadenfolgekosten
- Investitionskosten, Betriebskosten
- Sinnhaftigkeit & technische Realisierbarkeit (Zukunftsszenarien)
- Netzausbau, Stromtrassen
- magisches Dreieck

- Risikomatrix
    - Vor- und Nachbewertung der Risiken mit und ohne Maßnahmen
    - neue Überprüfung der Risikolevel (niedrig, mittel, hoch)
___

- Tools vertrauenswürdig?
- smardcast tool und bundesAPI validieren mit vorliegenden Daten
- über KI Codevalidierung und menschliche Überprüfung
- evtl. eigene API schreiben
___

### Software

- Einbindung von API zum Nutzen spezifischer Daten / aktuellster Daten
- modularer Aufbau, muss stets nutzbar sein
- Kernfeatures als erstes lauffähig machen
- schrittweise Erweiterung der Features
- Unit-Tests
- Validierung der Berechnungen mit bestehenden Daten oder anderen Tools wie Excel / KI
___

- Konvertierung verschiedener Dateiformate oder .csv Formatierungen einheitlich machen
- Benutzereingabe zur Auswahl der Quellen / Zeiträume / Datenpunkte
- Methoden vs Funktionen
- Modularisierung
    - Dateneinlesen & -verarbeiten
    - Umwandlung von verschiedenen Datentypen / -formaten
    - Plotting
    - UI
    - Interpolationsberechnung von Daten
- magic 3
- 

Berechnung von aktuellen Werten und wneiger oder mehr als 100% EEs um Speicher zu laden oder zu entladen, wieviel Speicher werden bemötigt? Verlustberechnung (Effizienz). Testberechnung der Kosten von Speichersystemen
(Werte erstmal als instant entladen und aufladen aus und ins Netz, danach vielleicht zeitliche Näherung, wie lang dauert es pro MWh zu laden oder entladen?)
wie verhalten sich Speicherparks bezüglich der Ladekurven / Effizienz?
Berechnung der Netto-EE-Erzeugung, dann bei Überschuss Speicher als nutzbare Energiequelle mit Einberechnung des Wirkungsgrads mit einberechnen.
berechnungsseitig alles in MWh oder besser in Wh?
Einbeziehung Wasserstoff -> schauen, was wo zuerst reinkommt -> Slider 50/50, 80/20 etc.

Baue Methode: Studie auswählen, Referenzjahr(e) eingeben können, mit der prognose für 2030 bis 2045 (je nachdem was verfügbar ist) ich das haben will und als dataframe ausspucken. Ins UI einbauen danach.
später einbauen: im winter mehr stromverbrauch wegen wärmepumpen, E-Autos sollen über Nacht geladen werden bisher ist der mehrverbrauch nur gemittelt über das gesamte jahr. Haben wir sowas wie eine Glockenkurve, die man über den Winter oder die Nacht legen kann? Steht dazu etwas in den Studien oder müssen wir selber eine solche Funktion modellieren?