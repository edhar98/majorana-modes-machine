.PHONY: all report clean cleanall

all: report

report: report.tex *.tex sections/*.tex *.bib
	pdflatex -interaction=nonstopmode report.tex
	-bibtex report.aux
	pdflatex -interaction=nonstopmode report.tex
	pdflatex -interaction=nonstopmode report.tex

clean:
	rm -f report.aux report.log report.out report.toc report.bbl report.blg

cleanall: clean
	rm -f report.pdf
