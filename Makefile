WEEKS := 1 2 3 4 5 6
WEEK_TARGETS := $(addprefix week,$(WEEKS))
WEEK_PDFS := $(addprefix presentation/week,$(addsuffix /slides.pdf,$(WEEKS)))
CLEAN_TARGETS := $(addprefix clean-week,$(WEEKS))
NOTE_TEX := $(wildcard notes/*.tex)
NOTE_PDFS := $(NOTE_TEX:.tex=.pdf)
PDFLATEX := pdflatex
LATEX_FLAGS := -interaction=nonstopmode -halt-on-error

ifeq ($(OS),Windows_NT)
CD := cd /d
NULL := NUL
native_path = $(subst /,\,$(1))
define delete_files
	-del /Q $(foreach f,$(1),$(call native_path,$(f))) 2>$(NULL)
endef
else
CD := cd
NULL := /dev/null
native_path = $(1)
define delete_files
	rm -f $(1)
endef
endif

.PHONY: all slides notes $(WEEK_TARGETS) clean clean-notes $(CLEAN_TARGETS)

all: slides notes

slides: $(WEEK_PDFS)

notes: $(NOTE_PDFS)

$(foreach week,$(WEEKS),$(eval week$(week): presentation/week$(week)/slides.pdf))

presentation/week%/slides.pdf: presentation/week%/slides.tex
	$(CD) $(call native_path,presentation/week$*) && $(PDFLATEX) $(LATEX_FLAGS) slides.tex
	$(CD) $(call native_path,presentation/week$*) && $(PDFLATEX) $(LATEX_FLAGS) slides.tex

presentation/week%/slides.tex:
	@echo "No slides.tex found for week$*"
	@exit 1

notes/%.pdf: notes/%.tex
	$(CD) notes && $(PDFLATEX) $(LATEX_FLAGS) $*.tex
	$(CD) notes && $(PDFLATEX) $(LATEX_FLAGS) $*.tex

clean: $(CLEAN_TARGETS) clean-notes

clean-notes:
	$(call delete_files, notes/*.aux notes/*.log notes/*.out notes/*.toc)

define clean_week_rule
clean-week$(1):
	$(call delete_files,\
		presentation/week$(1)/slides.aux \
		presentation/week$(1)/slides.log \
		presentation/week$(1)/slides.nav \
		presentation/week$(1)/slides.out \
		presentation/week$(1)/slides.snm \
		presentation/week$(1)/slides.toc \
		presentation/week$(1)/slides.vrb)
endef

$(foreach week,$(WEEKS),$(eval $(call clean_week_rule,$(week))))
