; AURENIX PRO — Dark Royal Gold Edition
; Compiled with Inno Setup 6 after BUILD_AURENIX_WINDOWS.bat succeeds.
#define AppName "AURENIX PRO"
#define AppVersion "1.1.0"
#define AppExe "AURENIX PRO.exe"

[Setup]
AppId={{0F1DCA17-1E0C-49B6-98F2-27DDB4E774A2}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName=AURENIX PRO - Dark Royal Gold Edition
DefaultDirName={localappdata}\Programs\AURENIX PRO
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=Installer
OutputBaseFilename=AURENIX-PRO-Dark-Royal-Gold-Windows-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExe}
CloseApplications=yes

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\AURENIX PRO\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch AURENIX PRO"; Flags: nowait postinstall skipifsilent
