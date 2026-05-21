@echo off
setlocal

if "%PDFLATEX%"=="" set "PDFLATEX=pdflatex"
if "%LATEX_FLAGS%"=="" set "LATEX_FLAGS=-interaction=nonstopmode -halt-on-error"

set "TARGET=%~1"
if "%TARGET%"=="" set "TARGET=all"

if /I "%TARGET%"=="all" (
  call :compile_week 1 || exit /b 1
  call :compile_week 2 || exit /b 1
  call :compile_week 3 || exit /b 1
  call :compile_week 4 || exit /b 1
  call :compile_week 5 || exit /b 1
  exit /b 0
)

if /I "%TARGET%"=="clean" (
  call :clean_week 1
  call :clean_week 2
  call :clean_week 3
  call :clean_week 4
  call :clean_week 5
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

echo Unknown target: %TARGET%
echo Usage: make week5 ^| make all ^| make clean-week5 ^| make clean
exit /b 1

:compile_week
set "WEEK=%~1"
set "WEEK_DIR=presentation\week%WEEK%"
if not exist "%WEEK_DIR%\slides.tex" (
  echo No slides.tex found for week%WEEK%
  exit /b 1
)
pushd "%WEEK_DIR%" || exit /b 1
%PDFLATEX% %LATEX_FLAGS% slides.tex || (popd & exit /b 1)
%PDFLATEX% %LATEX_FLAGS% slides.tex || (popd & exit /b 1)
popd
exit /b 0

:clean_week
set "WEEK=%~1"
set "WEEK_DIR=presentation\week%WEEK%"
del /Q "%WEEK_DIR%\slides.aux" "%WEEK_DIR%\slides.log" "%WEEK_DIR%\slides.nav" "%WEEK_DIR%\slides.out" "%WEEK_DIR%\slides.snm" "%WEEK_DIR%\slides.toc" "%WEEK_DIR%\slides.vrb" 2>NUL
exit /b 0
