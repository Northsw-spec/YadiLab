# SECURITY-LEGAL-001 — testbar säkerhet och ärliga rättighetsgränser

Status: normativt designkrav; implementation NOT_STARTED.

- Linux offline-first: backend lyssnar normalt bara på loopback eller OS-local IPC, CSRF/auth protections, kortlivade sessions, hårda resursgränser, immutable frontend origin, ingen generell offentlig port. Multiuser måste kunna fungera över autentiserad, explicit användaraktiverad peer-federering, krypterad och identitetskontrollerad, utan att läsa godtyckliga lokala filer eller scanna riktiga nät.
- Scripting: PT-stödda MCU/SBC/IoT Python/JS och Activity Wizard-script ska simuleras i strikt sandbox med resource quotas och deterministisk virtual-time, aldrig godtycklig os.environ, open(), subprocess, host NIC, raw shell, externa secrets. Säkerhet testas i linux sandbox-adapter innan skript tillåts i produkt.
- Import: XLSM makron, XLS/XLSB formula och PDF attachments, XML entities/DTD, YAML special constructors samt archive decompression får inte köras. Källan är data. En signerad/mergerad projektfil får bara sparas med uttrycklig action och konfliktkontroll.
- Protokoll: om verklig SSH/TLS/IPsec-kryptografi inte modelleras korrekt, märk modellen SIMULATED_SECURITY_LIMITATION; aldrig deklarera säker tunnel av en fake encrypt-knapp. Kontrollplansprotokoll exponeras inte på host interface.
- OT/PLC: YadiLab styr endast SIMULERADE industriella enheter. Ingen verklig PLC-/HMI-/ICS-kontroll eller utnyttjande av real nätverk via importerade scenarier.
- Cisco Packet Tracer-licens, varumärken, filformat, IOS CLI, ExApps, PKT/PKA/PKZ, firmware/modelldata, patents/IEC/IEEE/ODVA måste ha egen legitim specifikation och rätt till implementation/distribution. Proprietära filer får inte användas som latent emulator eller olagligt kopieras; "jag reverse-engineerade det" är inte automatiskt juridiskt godkänt.
- Om full kompatibilitet är juridiskt eller tekniskt otillgänglig, redovisa BLOCKED_LEGAL_OR_SPEC. FULL_PARITY får inte annonseras, och ingen funktion får strykas ur målet på grund av detta.
- Beroenden: versionslås, license inventory, SBOM, vulnerability handling, security regression on auth/import/exports, reproducible artifacts och regelbundet license review innan release.

Primär OWASP file-upload-guide: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html ; CSV injection https://owasp.org/www-community/attacks/CSV_Injection ; Qt WebEngine licens https://doc.qt.io/qtforpython-6/overviews/qtwebengine-licensing.html .
