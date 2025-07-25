adb push QPA_20250724_0001.png /storage/emulated/0/Pictures
adb shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///storage/emulated/0/Pictures/QPA_20250724_0001.png