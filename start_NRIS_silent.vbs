' ===================================================
'   NRIS Silent Launcher
'   Runs NRIS with minimized console window
'   Use this for a cleaner desktop experience
' ===================================================

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get script directory
scriptPath = fso.GetParentFolderName(WScript.ScriptFullName)

' Build command
batFile = scriptPath & "\start_NRIS_v2.bat"

' Check if bat file exists
If Not fso.FileExists(batFile) Then
    MsgBox "Error: start_NRIS_v2.bat not found!" & vbCrLf & _
           "Please make sure this file is in the NRIS folder.", _
           vbCritical, "NRIS Launcher Error"
    WScript.Quit
End If

' Run batch file minimized (7 = minimized, 0 = hidden)
' Using 7 (minimized) so user can still see it in taskbar if needed
WshShell.CurrentDirectory = scriptPath
WshShell.Run """" & batFile & """", 7, False

' Note: The browser will open automatically via the batch file
