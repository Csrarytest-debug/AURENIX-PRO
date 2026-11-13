#define MyAppName "AURENIX PRO BG Remover V0.7.3"
#define MyAppVersion "0.7.3"
[Setup]
AppId={{F21C771B-9994-4E4A-94AE-C75F02571CA2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\AURENIX PRO BG Remover V0.7.3
DefaultGroupName={#MyAppName}
OutputDir=Installer
OutputBaseFilename=AURENIX-PRO-BG-Remover-V0.7.3-Setup
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\AURENIX-PRO.exe
[Files]
Source: "dist\AURENIX-PRO\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autoprograms}\AURENIX PRO BG Remover V0.7.3"; Filename: "{app}\AURENIX-PRO.exe"
Name: "{autodesktop}\AURENIX PRO BG Remover V0.7.3"; Filename: "{app}\AURENIX-PRO.exe"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts"
[Run]
Filename: "{app}\AURENIX-PRO.exe"; Description: "Launch AURENIX PRO BG Remover V0.7.3"; Flags: nowait postinstall skipifsilent
