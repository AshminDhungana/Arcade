!include "MUI2.nsh"

!define PRODUCT_VERSION "1.0.0"  ; Override via `/DPRODUCT_VERSION=1.2.3` on makensis cmdline
!define PRODUCT_NAME "Arcade Launcher"
!define PRODUCT_PUBLISHER "Neurotech Biratnagar"
!define PRODUCT_WEB_SITE "https://github.com/neurotech-biratnagar/arcade"

Name "${PRODUCT_NAME}"
OutFile "Arcade-Setup-${PRODUCT_VERSION}.exe"
InstallDir "$PROGRAMFILES64\Arcade"
RequestExecutionLevel admin

!define MUI_ICON "assets/icon.ico"
!define MUI_UNICON "assets/icon.ico"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

Section "MainSection" SEC01
    SetOutPath "$INSTDIR"
    File /r "dist\arcade\*"
    CreateDirectory "$SMPROGRAMS\Arcade"
    CreateShortcut "$SMPROGRAMS\Arcade\Arcade Launcher.lnk" "$INSTDIR\arcade.exe"
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Arcade" "DisplayName" "${PRODUCT_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Arcade" "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Arcade" "Publisher" "${PRODUCT_PUBLISHER}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Arcade" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Arcade" "UninstallString" "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\*"
    RMDir /r "$INSTDIR"
    Delete "$SMPROGRAMS\Arcade\Arcade Launcher.lnk"
    RMDir "$SMPROGRAMS\Arcade"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Arcade"
SectionEnd
