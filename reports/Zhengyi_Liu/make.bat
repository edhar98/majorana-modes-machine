@echo off
setlocal EnableExtensions
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
exit /b 1
:report
%PDFLATEX% %LATEX_FLAGS% report.tex || exit /b 1
%BIBTEX% report
%PDFLATEX% %LATEX_FLAGS% report.tex || exit /b 1
%PDFLATEX% %LATEX_FLAGS% report.tex || exit /b 1
exit /b 0
:report_clean
%PDFLATEX% %LATEX_FLAGS% -jobname=report_clean "\def\hideai{}\input{report.tex}" || exit /b 1
%BIBTEX% report_clean
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
