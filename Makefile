all: haruhi-dl haruhi-dl.1 haruhi-dl.bash-completion haruhi-dl.zsh haruhi-dl.fish supportedsites

clean:
	rm -rf haruhi-dl.1.temp.md haruhi-dl.1 haruhi-dl.bash-completion MANIFEST build/ dist/ .coverage cover/ haruhi-dl.tar.gz haruhi-dl.zsh haruhi-dl.fish haruhi_dl/extractor/lazy_extractors.py *.dump *.part* *.ytdl *.info.json *.mp4 *.m4a *.flv *.mp3 *.avi *.mkv *.webm *.3gp *.wav *.ape *.swf *.jpg *.png CONTRIBUTING.md.tmp haruhi-dl haruhi-dl.exe
	find . -name "*.pyc" -delete
	find . -name "*.class" -delete

PREFIX ?= /usr/local
BINDIR ?= $(PREFIX)/bin
MANDIR ?= $(PREFIX)/man
SHAREDIR ?= $(PREFIX)/share
PYTHON ?= /usr/bin/env python

# set SYSCONFDIR to /etc if PREFIX=/usr or PREFIX=/usr/local
SYSCONFDIR = $(shell if [ $(PREFIX) = /usr -o $(PREFIX) = /usr/local ]; then echo /etc; else echo $(PREFIX)/etc; fi)

# set markdown input format to "markdown-smart" for pandoc version 2 and to "markdown" for pandoc prior to version 2
MARKDOWN = $(shell if [ `pandoc -v | head -n1 | cut -d" " -f2 | head -c1` = "2" ]; then echo markdown-smart; else echo markdown; fi)

install: haruhi-dl haruhi-dl.1 haruhi-dl.bash-completion haruhi-dl.zsh haruhi-dl.fish
	install -d $(DESTDIR)$(BINDIR)
	install -m 755 haruhi-dl $(DESTDIR)$(BINDIR)
	install -d $(DESTDIR)$(MANDIR)/man1
	install -m 644 haruhi-dl.1 $(DESTDIR)$(MANDIR)/man1
	install -d $(DESTDIR)$(SYSCONFDIR)/bash_completion.d
	install -m 644 haruhi-dl.bash-completion $(DESTDIR)$(SYSCONFDIR)/bash_completion.d/haruhi-dl
	install -d $(DESTDIR)$(SHAREDIR)/zsh/site-functions
	install -m 644 haruhi-dl.zsh $(DESTDIR)$(SHAREDIR)/zsh/site-functions/_haruhi-dl
	install -d $(DESTDIR)$(SYSCONFDIR)/fish/completions
	install -m 644 haruhi-dl.fish $(DESTDIR)$(SYSCONFDIR)/fish/completions/haruhi-dl.fish

codetest:
	flake8 .

test:
	#nosetests --with-coverage --cover-package=haruhi_dl --cover-html --verbose --processes 4 test
	nosetests --verbose test
	$(MAKE) codetest

ot: offlinetest

# Keep this list in sync with devscripts/run_tests.sh
offlinetest: codetest
	$(PYTHON) -m nose --verbose test \
		--exclude test_age_restriction.py \
		--exclude test_download.py \
		--exclude test_iqiyi_sdk_interpreter.py \
		--exclude test_socks.py \
		--exclude test_subtitles.py \
		--exclude test_write_annotations.py \
		--exclude test_youtube_lists.py \
		--exclude test_youtube_signature.py

tar: haruhi-dl.tar.gz

.PHONY: all clean install test tar bash-completion pypi-files zsh-completion fish-completion ot offlinetest codetest supportedsites

pypi-files: haruhi-dl.bash-completion haruhi-dl.1 haruhi-dl.fish

haruhi-dl: haruhi_dl/*.py haruhi_dl/*/*.py
	mkdir -p zip
	for d in haruhi_dl haruhi_dl/downloader haruhi_dl/extractor haruhi_dl/postprocessor ; do \
	  mkdir -p zip/$$d ;\
	  cp -pPR $$d/*.py zip/$$d/ ;\
	done
	touch -t 200001010101 zip/haruhi_dl/*.py zip/haruhi_dl/*/*.py
	mv zip/haruhi_dl/__main__.py zip/
	cd zip ; zip -q ../haruhi-dl haruhi_dl/*.py haruhi_dl/*/*.py __main__.py
	rm -rf zip
	echo '#!$(PYTHON)' > haruhi-dl
	cat haruhi-dl.zip >> haruhi-dl
	rm haruhi-dl.zip
	chmod a+x haruhi-dl

#README.md: haruhi_dl/*.py haruhi_dl/*/*.py
#	COLUMNS=80 $(PYTHON) haruhi_dl/__main__.py --help | $(PYTHON) devscripts/make_readme.py

#CONTRIBUTING.md: README.md
#	$(PYTHON) devscripts/make_contributing.py README.md CONTRIBUTING.md

issuetemplates: devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/1_broken_site.md .github/ISSUE_TEMPLATE_tmpl/2_site_support_request.md .github/ISSUE_TEMPLATE_tmpl/3_site_feature_request.md .github/ISSUE_TEMPLATE_tmpl/4_bug_report.md .github/ISSUE_TEMPLATE_tmpl/5_feature_request.md haruhi_dl/version.py
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/1_broken_site.md .github/ISSUE_TEMPLATE/1_broken_site.md
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/2_site_support_request.md .github/ISSUE_TEMPLATE/2_site_support_request.md
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/3_site_feature_request.md .github/ISSUE_TEMPLATE/3_site_feature_request.md
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/4_bug_report.md .github/ISSUE_TEMPLATE/4_bug_report.md
	$(PYTHON) devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/5_feature_request.md .github/ISSUE_TEMPLATE/5_feature_request.md

supportedsites:
	$(PYTHON) devscripts/make_supportedsites.py docs/supportedsites.md

#README.txt: README.md
#	pandoc -f $(MARKDOWN) -t plain README.md -o README.txt

haruhi-dl.1: README.md
	$(PYTHON) devscripts/prepare_manpage.py haruhi-dl.1.temp.md
	pandoc -s -f $(MARKDOWN) -t man haruhi-dl.1.temp.md -o haruhi-dl.1
	rm -f haruhi-dl.1.temp.md

haruhi-dl.bash-completion: haruhi_dl/*.py haruhi_dl/*/*.py devscripts/bash-completion.in
	$(PYTHON) devscripts/bash-completion.py

bash-completion: haruhi-dl.bash-completion

haruhi-dl.zsh: haruhi_dl/*.py haruhi_dl/*/*.py devscripts/zsh-completion.in
	$(PYTHON) devscripts/zsh-completion.py

zsh-completion: haruhi-dl.zsh

haruhi-dl.fish: haruhi_dl/*.py haruhi_dl/*/*.py devscripts/fish-completion.in
	$(PYTHON) devscripts/fish-completion.py

fish-completion: haruhi-dl.fish

lazy-extractors: haruhi_dl/extractor/lazy_extractors.py

_EXTRACTOR_FILES = $(shell find haruhi_dl/extractor -iname '*.py' -and -not -iname 'lazy_extractors.py')
haruhi_dl/extractor/lazy_extractors.py: devscripts/make_lazy_extractors.py devscripts/lazy_load_template.py $(_EXTRACTOR_FILES)
	$(PYTHON) devscripts/make_lazy_extractors.py $@

haruhi-dl.tar.gz: haruhi-dl haruhi-dl.1 haruhi-dl.bash-completion haruhi-dl.zsh haruhi-dl.fish ChangeLog AUTHORS
	@tar -czf haruhi-dl.tar.gz --transform "s|^|haruhi-dl/|" --owner 0 --group 0 \
		--exclude '*.DS_Store' \
		--exclude '*.kate-swp' \
		--exclude '*.pyc' \
		--exclude '*.pyo' \
		--exclude '*~' \
		--exclude '__pycache__' \
		--exclude '.git' \
		--exclude 'docs/_build' \
		-- \
		bin devscripts test haruhi_dl docs \
		ChangeLog AUTHORS LICENSE \
		Makefile MANIFEST.in haruhi-dl.1 haruhi-dl.bash-completion \
		haruhi-dl.zsh haruhi-dl.fish setup.py setup.cfg \
		haruhi-dl
