; Inno Setup script for the retuned standalone v1.0 release folder.
; Before compiling:
; 1. Run build_release_v1_0_retuned_standalone.ps1
; 2. Run: subst R: ..\release_candidates\Mr6_Auto_OCR_Pipeline_v1.0_retuned_standalone
; 3. Confirm R:\ is available and points to the standalone folder

#define MyAppName "Mr.6 Auto OCR Pipeline"
#define MyAppVersion "1.0"
#define MyAppPublisher "Sixmeister"
#define MyAppExeName "start_release_v1_0.bat"
#define MySourceDir "R:\"
#define MyOutputDir "..\release_installers"

[Setup]
AppId={{A3943B9F-7C5A-4753-A93B-6C79C066A0D8}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Mr6 Auto OCR Pipeline v1.0
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir={#MyOutputDir}
OutputBaseFilename=Mr6_Auto_OCR_Pipeline_v1.0_retuned_Setup
Compression=zip
SolidCompression=no
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#MySourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
