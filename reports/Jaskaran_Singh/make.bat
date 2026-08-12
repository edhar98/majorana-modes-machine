@echo off
setlocal EnableExtensions

rem Windows counterpart of the Unix makefile. On Windows cmd, typing `make`
rem runs this file, so the same commands work cross-platform:
rem   make               build report.pdf (AI purple) AND report_clean.pdf (AI hidden)
rem   make report        only report.pdf
rem   make report_clean  only report_clean.pdf
rem   make clean         remove aux/log/out/toc/bbl/blg
rem   make cleanall      also remove the PDFs
rem Double-clicking this file runs `make all` (both PDFs).

if "%PDFLATEX%"=="" set "PDFLATEX=pdflatex"
if "%BIBTEX%"=="" set "BIBTEX=bibtex"
if "%LATEX_FLAGS%"=="" set "LATEX_FLAGS=-interaction=nonstopmode"

set "TARGET=%~1"
if "%TARGET%"=="" set "TARGET=all"

if /I "%TARGET%"=="all" (
  call :report || exit /b 1
  call :report_clean || exit /b 1
  exit /b 0
)
if /I "%TARGET%"=="report"       ( call :report       & exit /b %ERRORLEVEL% )
if /I "%TARGET%"=="report_clean" ( call :report_clean & exit /b %ERRORLEVEL% )
if /I "%TARGET%"=="clean"        ( call :clean      & exit /b 0 )
if /I "%TARGET%"=="cleanall"     ( call :clean & call :cleanall & exit /b 0 )

echo Unknown target: %TARGET%
echo Usage: make ^| make report ^| make report_clean ^| make clean ^| make cleanall
exit /b 1

:report
%PDFLATEX% %LATEX_FLAGS% report.tex || exit /b 1
rem bibtex may exit nonzero (e.g. no citations); do not abort on it.
%BIBTEX% report.aux
%PDFLATEX% %LATEX_FLAGS% report.tex || exit /b 1
%PDFLATEX% %LATEX_FLAGS% report.tex || exit /b 1
exit /b 0

:report_clean
rem The clean build hides \ai{} text via \hideai.
%PDFLATEX% %LATEX_FLAGS% -jobname=report_clean "\def\hideai{}\input{report.tex}" || exit /b 1
%BIBTEX% report_clean.aux
%PDFLATEX% %LATEX_FLAGS% -jobname=report_clean "\def\hideai{}\input{report.tex}" || exit /b 1
%PDFLATEX% %LATEX_FLAGS% -jobname=report_clean "\def\hideai{}\input{report.tex}" || exit /b 1
exit /b 0

:clean
del /Q report.aux report.log report.out report.toc report.bbl report.blg 2>NUL
del /Q report_clean.aux report_clean.log report_clean.out report_clean.toc report_clean.bbl report_clean.blg 2>NUL
exit /b 0

:cleanall
del /Q report.pdf report_clean.pdf 2>NUL
exit /b 0
