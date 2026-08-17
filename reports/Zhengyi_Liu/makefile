.PHONY: all report report_clean clean cleanall

PDFLATEX ?= pdflatex
BIBTEX ?= bibtex
LATEX_FLAGS ?= -interaction=nonstopmode -halt-on-error

all: report report_clean

report: report.tex sections/*.tex references.bib
	$(PDFLATEX) $(LATEX_FLAGS) report.tex
	-$(BIBTEX) report
	$(PDFLATEX) $(LATEX_FLAGS) report.tex
	$(PDFLATEX) $(LATEX_FLAGS) report.tex

# The clean build hides \ai{} text; if all citations are inside \ai{}, BibTeX can
# exit nonzero because the clean .aux has no citations. The leading '-' is intentional.
report_clean: report.tex sections/*.tex references.bib
	$(PDFLATEX) $(LATEX_FLAGS) -jobname=report_clean "\def\hideai{}\input{report.tex}"
	-$(BIBTEX) report_clean
	$(PDFLATEX) $(LATEX_FLAGS) -jobname=report_clean "\def\hideai{}\input{report.tex}"
	$(PDFLATEX) $(LATEX_FLAGS) -jobname=report_clean "\def\hideai{}\input{report.tex}"

clean:
	rm -f report.aux report.log report.out report.toc report.bbl report.blg \
	      report_clean.aux report_clean.log report_clean.out report_clean.toc \
	      report_clean.bbl report_clean.blg

cleanall: clean
	rm -f report.pdf report_clean.pdf
