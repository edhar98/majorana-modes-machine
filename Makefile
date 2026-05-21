WEEKS := 1 2 3 4 5
WEEK_TARGETS := $(addprefix week,$(WEEKS))
CLEAN_TARGETS := $(addprefix clean-week,$(WEEKS))
PDFLATEX := pdflatex
LATEX_FLAGS := -interaction=nonstopmode -halt-on-error

.PHONY: all $(WEEK_TARGETS) clean $(CLEAN_TARGETS) FORCE

all: $(WEEK_TARGETS)

$(WEEK_TARGETS): FORCE
	@if [ ! -f presentation/$@/slides.tex ]; then \
		echo "No slides.tex found for $@"; \
		exit 1; \
	fi
	cd presentation/$@ && $(PDFLATEX) $(LATEX_FLAGS) slides.tex
	cd presentation/$@ && $(PDFLATEX) $(LATEX_FLAGS) slides.tex

presentation/week%/slides.pdf: presentation/week%/slides.tex
	cd presentation/week$* && $(PDFLATEX) $(LATEX_FLAGS) slides.tex
	cd presentation/week$* && $(PDFLATEX) $(LATEX_FLAGS) slides.tex

presentation/week%/slides.tex:
	@echo "No slides.tex found for week$*"
	@exit 1

clean: $(CLEAN_TARGETS)

$(CLEAN_TARGETS): clean-week%:
	rm -f presentation/week$*/slides.aux \
		presentation/week$*/slides.log \
		presentation/week$*/slides.nav \
		presentation/week$*/slides.out \
		presentation/week$*/slides.snm \
		presentation/week$*/slides.toc \
		presentation/week$*/slides.vrb

FORCE:
