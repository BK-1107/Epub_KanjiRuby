@echo off
chcp 65001 > nul
echo ============================================================
echo  Japanese EPUB Kanji Ruby Annotator - Batch Processor
echo ============================================================
echo.

:: Change directory to the folder where this batch file is located
cd /d "%~dp0"

:: Execute the batch processor
python epub_helper.py batch

echo.
echo ============================================================
echo  All EPUB files processed successfully!
echo ============================================================
echo.
pause
