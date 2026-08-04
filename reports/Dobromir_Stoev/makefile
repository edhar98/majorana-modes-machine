.PHONY: all report report_clean clean cleanall

all: report report_clean

report: report.tex *.tex sections/*.tex *.bib
	pdflatex -interaction=nonstopmode report.tex
	-bibtex report.aux
	pdflatex -interaction=nonstopmode report.tex
	pdflatex -interaction=nonstopmode report.tex

# The clean build hides \ai{} text; if every \cite lived inside \ai{}, its .aux
# has no citations and bibtex exits nonzero -- the leading '-' keeps make going.
report_clean: report.tex *.tex sections/*.tex *.bib
	pdflatex -interaction=nonstopmode -jobname=report_clean "\\def\\hideai{}\\input{report.tex}"
	-bibtex report_clean.aux
	pdflatex -interaction=nonstopmode -jobname=report_clean "\\def\\hideai{}\\input{report.tex}"
	pdflatex -interaction=nonstopmode -jobname=report_clean "\\def\\hideai{}\\input{report.tex}"

clean:
	rm -f report.aux report.log report.out report.toc report.bbl report.blg report_clean.aux report_clean.log report_clean.out report_clean.toc report_clean.bbl report_clean.blg

cleanall: clean
	rm -f report.pdf report_clean.pdf
