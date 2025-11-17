; finance-tracker-installer.iss

[Setup]
AppId={{F8F3F6B2-3E5C-4E3D-9A63-FTFINANCETRACKER}}
AppName=Personal Finance Tracker
AppVersion=0.1.0
AppPublisher=Marcos Kemer
DefaultDirName={autopf}\FinanceTracker
DefaultGroupName=Finance Tracker
DisableDirPage=no
DisableProgramGroupPage=no
OutputDir=.
OutputBaseFilename=FinanceTrackerSetup
SetupIconFile=..\finance_tracker_icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; Main executable and support files
Source: "..\dist\finance-tracker.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\.env"; DestDir: "{app}"; Flags: ignoreversion

; Icon file
Source: "..\finance_tracker_icon.ico"; DestDir: "{app}"; Flags: ignoreversion

; If you generate any extra DLLs or files in dist, add them here, e.g.:
; Source: "..\dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu
Name: "{group}\Finance Tracker"; Filename: "{app}\finance-tracker.exe"; IconFilename: "{app}\finance_tracker_icon.ico"
; Desktop
Name: "{commondesktop}\Finance Tracker"; Filename: "{app}\finance-tracker.exe"; Tasks: desktopicon; IconFilename: "{app}\finance_tracker_icon.ico"

[Run]
Filename: "{app}\finance-tracker.exe"; Description: "Launch Finance Tracker"; Flags: nowait postinstall skipifsilent
