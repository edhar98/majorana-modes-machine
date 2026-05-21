WEEKS := 1 2 3 4 5
WEEK_TARGETS := $(addprefix week,$(WEEKS))
CLEAN_TARGETS := $(addprefix clean-week,$(WEEKS))
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

.PHONY: all $(WEEK_TARGETS) clean $(CLEAN_TARGETS)

all: $(WEEK_TARGETS)

define week_rule
week$(1): presentation/week$(1)/slides.tex
	$(CD) $(call native_path,presentation/week$(1)) && $(PDFLATEX) $(LATEX_FLAGS) slides.tex
	$(CD) $(call native_path,presentation/week$(1)) && $(PDFLATEX) $(LATEX_FLAGS) slides.tex

presentation/week$(1)/slides.pdf: presentation/week$(1)/slides.tex
	$(CD) $(call native_path,presentation/week$(1)) && $(PDFLATEX) $(LATEX_FLAGS) slides.tex
	$(CD) $(call native_path,presentation/week$(1)) && $(PDFLATEX) $(LATEX_FLAGS) slides.tex

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

$(foreach week,$(WEEKS),$(eval $(call week_rule,$(week))))

presentation/week%/slides.tex:
	@echo "No slides.tex found for week$*"
	@exit 1

clean: $(CLEAN_TARGETS)
