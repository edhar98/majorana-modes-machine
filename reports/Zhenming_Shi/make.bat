@echo off
setlocal EnableExtensions

rem Windows counterpart of the Unix makefile. On Windows cmd, typing `make`
rem runs this file, so the same commands work cross-platform:
rem   make            build report.pdf
rem   make report     same
rem   make clean      remove aux/log/out/toc/bbl/blg
rem   make cleanall   also remove report.pdf
rem Double-clicking this file runs `make all`.

if "%PDFLATEX%"=="" set "PDFLATEX=pdflatex"
if "%BIBTEX%"=="" set "BIBTEX=bibtex"
if "%LATEX_FLAGS%"=="" set "LATEX_FLAGS=-interaction=nonstopmode"

set "TARGET=%~1"
if "%TARGET%"=="" set "TARGET=all"

if /I "%TARGET%"=="all"      ( call :report & exit /b %ERRORLEVEL% )
if /I "%TARGET%"=="report"   ( call :report & exit /b %ERRORLEVEL% )
if /I "%TARGET%"=="clean"    ( call :clean  & exit /b 0 )
if /I "%TARGET%"=="cleanall" ( call :clean & call :cleanall & exit /b 0 )

echo Unknown target: %TARGET%
echo Usage: make ^| make report ^| make clean ^| make cleanall
exit /b 1

:report
%PDFLATEX% %LATEX_FLAGS% report.tex || exit /b 1
rem bibtex may exit nonzero (e.g. no citations); do not abort on it.
%BIBTEX% report.aux
%PDFLATEX% %LATEX_FLAGS% report.tex || exit /b 1
%PDFLATEX% %LATEX_FLAGS% report.tex || exit /b 1
exit /b 0

:clean
del /Q report.aux report.log report.out report.toc report.bbl report.blg 2>NUL
exit /b 0

:cleanall
del /Q report.pdf 2>NUL
exit /b 0
