; Rapport NSIS 安装器脚本
; 把 PyInstaller 的 onedir 产物 dist\Rapport\ 装进 $PROGRAMFILES64\Rapport，
; 建开始菜单 + 桌面快捷方式、卸载器，提供「开机自启」可选项。
;
; 编译（装好 NSIS 后，在仓库根执行）：
;   "C:\Program Files (x86)\NSIS\makensis.exe" packaging\installer.nsi
; 产出：packaging\RapportSetup.exe
;
; 前置：先跑过 PyInstaller，dist\Rapport\Rapport.exe 必须存在。

Unicode true

!define APPNAME "Rapport"
!define COMPANYNAME "Rapport"
!define DESCRIPTION "本地优先的人际对话助手（托盘常驻）"
!define APPEXE "Rapport.exe"

; 版本（与 pyproject 对齐，手动维护）。
!define VERSIONMAJOR 0
!define VERSIONMINOR 0
!define VERSIONBUILD 1

!include "MUI2.nsh"
!include "LogicLib.nsh"

Name "${APPNAME}"
OutFile "RapportSetup.exe"
; 64 位默认 Program Files；onedir 是 64 位产物。
InstallDir "$PROGRAMFILES64\${APPNAME}"
InstallDirRegKey HKLM "Software\${APPNAME}" "InstallDir"
RequestExecutionLevel admin  ; 写 Program Files + 卸载注册表需要管理员。

!define MUI_ABORTWARNING
; 有自定义图标就用（与 PyInstaller 同一枚 rapport.ico）；没有则用 NSIS 默认图标。
; P3 未提供 .ico 时这两段不展开，安装器仍能正常编译。
!if /FileExists "rapport.ico"
  !define MUI_ICON "rapport.ico"
  !define MUI_UNICON "rapport.ico"
!endif

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
; 自定义页：开机自启复选框。
Page custom AutostartPage AutostartPageLeave
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "English"

Var AutostartCheckbox
Var AutostartEnabled

Function AutostartPage
  nsDialogs::Create 1018
  Pop $0
  ${NSD_CreateCheckbox} 0 20u 100% 12u "开机时自动启动 Rapport（登录后托盘常驻录音）"
  Pop $AutostartCheckbox
  ; 默认不勾选，尊重隐私（常驻录音是敏感行为）。
  nsDialogs::Show
FunctionEnd

Function AutostartPageLeave
  ${NSD_GetState} $AutostartCheckbox $AutostartEnabled
FunctionEnd

Section "安装" SecInstall
  SetOutPath "$INSTDIR"
  ; 递归装入整个 onedir 产物（dist\Rapport\ 下全部内容）。
  File /r "..\dist\Rapport\*.*"

  ; 开始菜单 + 桌面快捷方式。
  CreateDirectory "$SMPROGRAMS\${APPNAME}"
  CreateShortcut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" "$INSTDIR\${APPEXE}"
  CreateShortcut "$SMPROGRAMS\${APPNAME}\卸载 ${APPNAME}.lnk" "$INSTDIR\uninstall.exe"
  CreateShortcut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\${APPEXE}"

  ; 可选开机自启：写当前用户 Run 键。
  ${If} $AutostartEnabled == ${BST_CHECKED}
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "${APPNAME}" '"$INSTDIR\${APPEXE}"'
  ${EndIf}

  ; 记录安装目录 + 写卸载器与「添加或删除程序」注册项。
  WriteRegStr HKLM "Software\${APPNAME}" "InstallDir" "$INSTDIR"
  WriteUninstaller "$INSTDIR\uninstall.exe"

  !define UNINSTKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"
  WriteRegStr HKLM "${UNINSTKEY}" "DisplayName" "${APPNAME} - ${DESCRIPTION}"
  WriteRegStr HKLM "${UNINSTKEY}" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegStr HKLM "${UNINSTKEY}" "DisplayIcon" "$INSTDIR\${APPEXE}"
  WriteRegStr HKLM "${UNINSTKEY}" "Publisher" "${COMPANYNAME}"
  WriteRegStr HKLM "${UNINSTKEY}" "DisplayVersion" "${VERSIONMAJOR}.${VERSIONMINOR}.${VERSIONBUILD}"
  WriteRegDWORD HKLM "${UNINSTKEY}" "NoModify" 1
  WriteRegDWORD HKLM "${UNINSTKEY}" "NoRepair" 1
SectionEnd

Section "Uninstall"
  ; 停掉可能在跑的进程（卸载前），忽略失败。
  ExecWait 'taskkill /F /IM ${APPEXE}' $0

  Delete "$DESKTOP\${APPNAME}.lnk"
  Delete "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk"
  Delete "$SMPROGRAMS\${APPNAME}\卸载 ${APPNAME}.lnk"
  RMDir "$SMPROGRAMS\${APPNAME}"

  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "${APPNAME}"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"
  DeleteRegKey HKLM "Software\${APPNAME}"

  ; 删安装目录全部内容。注意：用户数据在 %LOCALAPPDATA%\Rapport，不在此删除（保留）。
  RMDir /r "$INSTDIR"
SectionEnd
