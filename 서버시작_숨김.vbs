' PicPod 관상 분석 서버 - 창 없이 백그라운드 실행 (시작프로그램용)
Set sh = CreateObject("WScript.Shell")
base = "C:\picpod_face_analysis"
sh.CurrentDirectory = base
' Ollama가 꺼져 있으면 켠다 (이미 떠 있으면 조용히 실패, 무해)
On Error Resume Next
sh.Run """" & sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Ollama\ollama.exe"" serve", 0, False
WScript.Sleep 3000
sh.Run """" & base & "\.venv\Scripts\python.exe"" -m uvicorn app.main:app --host 0.0.0.0 --port 8123", 0, False
