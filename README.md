# QRIS Payment Automation

## Build Windows

```
pyinstaller --onefile --noconsole --name qris_auto_pay ^
  --add-binary "adb/windows/adb.exe;adb/windows" ^
  --add-binary "adb/windows/AdbWinApi.dll;adb/windows" ^
  --add-binary "adb/windows/AdbWinUsbApi.dll;adb/windows" ^
  app.py
```  