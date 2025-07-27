# QRIS Payment Automation

## Build Windows

```
pyinstaller --onefile --noconsole --name qris_auto_pay ^
  --add-data ".env;." ^
  --add-binary "embed/adb/windows/adb.exe;embed/adb/windows" ^
  --add-binary "embed/adb/windows/AdbWinApi.dll;embed/adb/windows" ^
  --add-binary "embed/adb/windows/AdbWinUsbApi.dll;embed/adb/windows" ^
  app3.py
```  