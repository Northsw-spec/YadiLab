# IMPORT-001 — import av alla viktiga nätverksdokument

**Same-UI-importkrav:** [LEGACY-UI-FIDELITY-001](LEGACY_UI_FIDELITY_CONTRACT.md) kräver att nya appens importdialog och arbetsresa motsvarar [YadiLab_legacy @ aac82926ced3dbf4cac09242530762ac3da1fe80](https://github.com/Northsw-spec/YadiLab_legacy/tree/aac82926ced3dbf4cac09242530762ac3da1fe80): originalfiler/preview -> MappingViews/profiler/radbeslut -> granskningsplan/kandidat -> explicit tillämpning och historisk proveniens med bundle export/reattach. Nya XLS/XLSB/YAML/XML-format utökar detsamma, men får inte ersätta eller dölja originalflödet. Importens arbetsyta triggar automatiskt första ELK efter accepterat projekt, men aldrig implicit Save. Faktisk ny implementation och Chromium-verifiering NOT_RUN.

Status DESIGN_ONLY; inga nya filadaptrar har testats i detta tomma repo.

## Obligatoriska och framtida format
**Prioritet A:** CSV, TSV, semikolonavgränsad TXT, XLS/XLSX/XLSM/XLSB, ODS, strikt JSON, YAML, XML, export till native JSON/CSV/XLSX/ODS. Källcellens exakta position och text, originalbytes, formel kontra cached value, schema och provenance ska kunna visas.
**Prioritet B:** tabellorienterad PDF, DOCX, HTML, GraphML, draw.io/mxGraph, Visio VSDX, NetBox/IPAM/CMDB-exporter, när lagliga verkliga exempel och testade läsare finns. OCR/scannade PDF:er och frihandsskisser är låg evidens: endast manuell granskning, aldrig automatiskt konstruerade fakta.

Oberoende läsarunderlag: pandas read_excel med calamine har dokumenterat .xls/.xlsx/.xlsm/.xlsb/.ods-stöd, men detta är LIBRARY_CAPABILITY, inte bevis att YadiLabs framtida importer fungerar. https://pandas.pydata.org/pandas-docs/stable/generated/pandas.read_excel.html . openpyxl har read_only/data_only/keep_links-kontroller: https://openpyxl.readthedocs.io/en/stable/api/openpyxl.reader.excel.html . Kontrollera valda API-versioner med egna verkliga testfiler.

## Säkra importsteg – den enda vägen
1. Bounded raw upload, content magic/schema detection, max compressed/uncompressed size, parser timeout, sheet count, row count, cells/column count, recursion depth, Unicode normalization checks. Inga makron, externa Excel-links, XML entities, YAML object constructors eller scripts körs.
2. Bevara SHA256 raw bytes, filnamn, format, parser version och formler (utan att exekvera dem); varje resultat har sheet/table/row/column/cell eller exakt source JSON path och den ursprungliga texten.
3. Preview visar source ranges, header choice, column→field map, per-row allow/reject/repair, ValueMap, constants med ursprungsmarkering och datatyp; saknade källor bekräftas av användaren.
4. En föreslagen topo/kandidat skapas UTAN att mutera användarprojektet. Kabel kräver två EXPLICITA port endpoints eller separat användarritad godkänd link. Namn, närhet, IP-subnet, VLAN och ELK-route ger aldrig inferred cable.
5. Konflikter blockeras: duplicate device/port/cable, IP/CIDR overlap, invalid IPv6/IPv4 host, VLAN mismatch, conflicting route, invalid MAC, import source override som inte accepterats.
6. Atomiskt projektcommit vid explicit review. Ingen simulation körs när dokument läses; failed import gör ingen Save. Export bevarar provenance och skyddar CSV formula injection.

OWASP risks: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html och https://owasp.org/www-community/attacks/CSV_Injection .

## Minimum golden fixtures
CSV UTF-8 BOM, CSV semicolon/tab, embedded newline, comments, duplicate headers, inconsistent fields, .xlsx multi-sheet/merged cells/formulas, .xls and .xlsb real binary, .ods real workbook, .xlsm macro present but never executed, duplicate JSON key, malformed XML, formula injection, zip bomb, overly large sheet, mixed IPv6/IPv4, source cell provenance mapping, missing two-port cable. Varje format får status VERIFIED först när programmatisk fixture testat just den varianten. Tillstånd: PARSED_SOURCES ≠ COMMITTED_VALID_TOPOLOGY ≠ SIMULATED_NETWORK.
