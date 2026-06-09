@echo off
setlocal EnableExtensions EnableDelayedExpansion

if "%PDFLATEX%"=="" set "PDFLATEX=pdflatex"
if "%LATEX_FLAGS%"=="" set "LATEX_FLAGS=-interaction=nonstopmode -halt-on-error"

set "TARGET=%~1"
if "%TARGET%"=="" set "TARGET=all"

if /I "%TARGET%"=="all" (
  call :compile_all_weeks || exit /b 1
  call :compile_notes || exit /b 1
  exit /b 0
)

if /I "%TARGET%"=="slides" (
  call :compile_all_weeks
  exit /b %ERRORLEVEL%
)

if /I "%TARGET%"=="notes" (
  call :compile_notes
  exit /b %ERRORLEVEL%
)

if /I "%TARGET%"=="clean" (
  call :clean_all_weeks
  call :clean_notes
  exit /b 0
)

if /I "%TARGET%"=="clean-notes" (
  call :clean_notes
  exit /b 0
)

if /I "%TARGET:~0,4%"=="week" (
  call :compile_week %TARGET:~4%
  exit /b %ERRORLEVEL%
)

if /I "%TARGET:~0,10%"=="clean-week" (
  call :clean_week %TARGET:~10%
  exit /b 0
)

if /I "%TARGET:~0,5%"=="note-" (
  call :compile_note "%TARGET:~5%"
  exit /b %ERRORLEVEL%
)

echo Unknown target: %TARGET%
echo Usage: make week6 ^| make notes ^| make note-week6_phase_sweep ^| make all ^| make clean
exit /b 1

:compile_all_weeks
for %%W in (1 2 3 4 5 6 7) do call :compile_week %%W || exit /b 1
exit /b 0

:clean_all_weeks
for %%W in (1 2 3 4 5 6 7) do call :clean_week %%W
exit /b 0

:compile_week
set "WEEK=%~1"
set "WEEK_DIR=presentation\week%WEEK%"
set "TEX=%WEEK_DIR%\slides.tex"
set "PDF=%WEEK_DIR%\slides.pdf"
if not exist "%TEX%" (
  echo No slides.tex found for week%WEEK%
  exit /b 1
)
call :is_outdated "%TEX%" "%PDF%"
if errorlevel 1 (
  echo [skip] week%WEEK% slides are up to date
  exit /b 0
)
pushd "%WEEK_DIR%" || exit /b 1
%PDFLATEX% %LATEX_FLAGS% slides.tex || (popd & exit /b 1)
%PDFLATEX% %LATEX_FLAGS% slides.tex || (popd & exit /b 1)
popd
exit /b 0

:compile_notes
for %%F in (notes\*.tex) do call :compile_note "%%~nF" || exit /b 1
exit /b 0

:compile_note
set "NAME=%~1"
set "TEX=notes\%NAME%.tex"
set "PDF=notes\%NAME%.pdf"
if not exist "%TEX%" (
  echo No note found: %TEX%
  exit /b 1
)
call :is_outdated "%TEX%" "%PDF%"
if errorlevel 1 (
  echo [skip] %NAME% note is up to date
  exit /b 0
)
pushd notes || exit /b 1
%PDFLATEX% %LATEX_FLAGS% "%NAME%.tex" || (popd & exit /b 1)
%PDFLATEX% %LATEX_FLAGS% "%NAME%.tex" || (popd & exit /b 1)
popd
exit /b 0

:is_outdated
set "SRC=%~1"
set "OUT=%~2"
if not exist "%OUT%" exit /b 0
for %%I in ("%SRC%") do set "SRC_TIME=%%~tI"
for %%I in ("%OUT%") do set "OUT_TIME=%%~tI"
if "%SRC_TIME%" GTR "%OUT_TIME%" exit /b 0
exit /b 1

:clean_week
set "WEEK=%~1"
set "WEEK_DIR=presentation\week%WEEK%"
del /Q "%WEEK_DIR%\slides.aux" "%WEEK_DIR%\slides.log" "%WEEK_DIR%\slides.nav" "%WEEK_DIR%\slides.out" "%WEEK_DIR%\slides.snm" "%WEEK_DIR%\slides.toc" "%WEEK_DIR%\slides.vrb" 2>NUL
exit /b 0

:clean_notes
del /Q "notes\*.aux" "notes\*.log" "notes\*.out" "notes\*.toc" 2>NUL
exit /b 0
