PYTHON_FILES =				\
	editorwindow.py			\
	profilesdialog.py		\
	aboutdialog.py			\
	saveconfirm.py			\
	gconfviewer.py			\
	fileviewer.py			\
	usersdialog.py			\
	groupsdialog.py		\
	sessionwindow.py		\
	sessionwidget.py		\
	lockdownappliersabayon.py	\
	changeswindow.py

@INTLTOOL_DESKTOP_RULE@

UI_FILES =				\
	sabayon.ui

desktopdir        = $(datadir)/applications
desktop_in_files = sabayon.desktop.in
desktop_DATA     = $(desktop_in_files:.desktop.in=.desktop)

EXTRA_DIST =				\
	$(PYTHON_FILES)			\
	$(UI_FILES)			\
	$(desktop_in_files)		\
	$(desktop_DATA)			\
	sabayon				\
	sabayon-apply			\
	sabayon-session			\
	sabayon.console.in		\
	sabayon.pam			\
	sabayon-xinitrc.sh.in

uidir   = $(pkgdatadir)/ui
ui_DATA = $(UI_FILES)

bin_SCRIPTS = sabayon
sbin_SCRIPTS = sabayon-apply
libexec_SCRIPTS = sabayon-session

sabayondir     = $(pyexecdir)/sabayon
sabayon_PYTHON = $(PYTHON_FILES)

%.sh: %.sh.in
	sed                                             \
		-e s!\@SBINDIR\@!$(sbindir)!g            \
		-e s!\@SCONFDIR\@!$(sysconfdir)!g        \
		< $< > $@
	chmod a+x $@

if INSTALL_XINITRC_SCRIPT
xinitrcdir      = $(sysconfdir)/$(XINITRC_SYSCONFDIR)
xinitrc_SCRIPTS = sabayon-xinitrc.sh
endif

install-exec-local:
	mkdir -p $(DESTDIR)$(sysconfdir)/sabayon/profiles/
if CONSOLE_HELPER
	$(INSTALL_DATA) -D $(srcdir)/sabayon.pam $(DESTDIR)$(PAM_PREFIX)/pam.d/sabayon
	$(INSTALL_DATA) -D sabayon.console $(DESTDIR)$(PAM_PREFIX)/security/console.apps/sabayon
	$(INSTALL_DATA) -m 755 -d $(DESTDIR)$(sbindir)
	mv -f $(DESTDIR)$(bindir)/sabayon $(DESTDIR)$(sbindir)
	$(LN_S) @CONSOLE_HELPER@ $(DESTDIR)$(bindir)/sabayon
endif

uninstall-local:
	rmdir --ignore-fail-on-non-empty $(DESTDIR)$(sysconfdir)/sabayon/profiles/
	rmdir --ignore-fail-on-non-empty $(DESTDIR)$(sysconfdir)/sabayon/
if CONSOLE_HELPER
	rm -f $(DESTDIR)$(PAM_PREFIX)/pam.d/sabayon
	rm -f $(DESTDIR)$(PAM_PREFIX)/security/console.apps/sabayon
	rmdir --ignore-fail-on-non-empty $(DESTDIR)$(PAM_PREFIX)/pam.d
	rmdir --ignore-fail-on-non-empty $(DESTDIR)$(PAM_PREFIX)/security/console.apps
endif

pycheck:
	pychecker -F $(top_srcdir)/pycheckrc $(PYTHON_FILES)

clean:
	rm -f *.pyo *.pyc

DISTCLEANFILES =		\
	$(desktop_DATA)		\
	sabayon-xinitrc.sh
