"""Generate ClaudeMeter.vbs launcher."""
import sys
import os

app_dir = os.path.dirname(os.path.abspath(__file__))
pythonw = sys.executable.replace("python.exe", "pythonw.exe")

vbs = f'''Set fso = CreateObject("Scripting.FileSystemObject")
myDir = fso.GetParentFolderName(WScript.ScriptFullName)
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = myDir
WshShell.Run Chr(34) & "{pythonw}" & Chr(34) & " " & Chr(34) & myDir & "\\claude_meter.py" & Chr(34), 0, False
'''

vbs_path = os.path.join(app_dir, "ClaudeMeter.vbs")
with open(vbs_path, "w") as f:
    f.write(vbs)
print(f"[OK] Launcher created: {vbs_path}")
