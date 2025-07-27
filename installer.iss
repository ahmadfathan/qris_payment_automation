[Setup]
AppName=Test App
AppVersion=1.0
DefaultDirName={pf}\TestApp
DefaultGroupName=TestApp
OutputDir=output
OutputBaseFilename=setup

[Files]
Source: "C:\Users\ghooz\Downloads\node-v22.17.1-win-x64\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Code]
type
  WPARAM = LongWord;
  LPARAM = LongInt;
  //UINT = LongWord;
  //HWND = LongWord;
  //DWORD = LongWord;
  
const
  WM_SETTINGCHANGE = $001A;
  //HWND_BROADCAST = $FFFF;
  SMTO_ABORTIFHUNG = $0002;

function SendMessageTimeout(hWnd: HWND; Msg: UINT; wParam: WPARAM; lParam: string;
  fuFlags, uTimeout: UINT; var lpdwResult: DWORD): DWORD;
  external 'SendMessageTimeoutA@user32.dll stdcall';

procedure BroadcastEnvironmentChange;
var
  resultCode: DWORD;
begin
  SendMessageTimeout(HWND_BROADCAST, WM_SETTINGCHANGE, 0, 'Environment',
                     SMTO_ABORTIFHUNG, 5000, resultCode);
end;

function AddToUserPath(dirToAdd: string): Boolean;
var
  oldPath, newPath: string;
begin
  if RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', oldPath) then
  begin
    if Pos(LowerCase(dirToAdd), LowerCase(oldPath)) = 0 then
    begin
      if (Length(oldPath) > 0) and (oldPath[Length(oldPath)] <> ';') then
        oldPath := oldPath + ';';
      newPath := oldPath + dirToAdd;
      Result := RegWriteStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', newPath);
    end
    else
      Result := True;
  end
  else
    Result := RegWriteStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', dirToAdd);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  nodePath: string;
  success: Boolean;
  resultCode: Integer;
  
begin
  if CurStep = ssPostInstall then
  begin
    nodePath := ExpandConstant('{app}\node-v22.17.1-win-x64');

    if AddToUserPath(nodePath) then
    begin
      BroadcastEnvironmentChange;

      MsgBox('Node.js added to PATH. Now installing Appium and uiautomator2 driver...',
             mbInformation, MB_OK);

      success :=
        Exec(ExpandConstant('{app}\node-v22.17.1-win-x64\npm.cmd'), 'install -g appium',
             '', SW_SHOW, ewWaitUntilTerminated, resultCode) and
        Exec(ExpandConstant('{app}\node-v22.17.1-win-x64\npx.cmd'),
             'appium driver install uiautomator2',
             '', SW_SHOW, ewWaitUntilTerminated, resultCode);

      if success then
        MsgBox('✅ Appium and uiautomator2 installed successfully.', mbInformation, MB_OK)
      else
        MsgBox('❌ Appium installation failed. Please check your internet connection or retry manually.', mbError, MB_OK);
    end
    else
    begin
      MsgBox('Failed to add Node.js to PATH. Appium install skipped.', mbError, MB_OK);
    end;
  end;
end;