# ENCflow/test/gvchange/Makefile
#   空隙率変更手続き m_state_set_gv(developer.md §63.1 A2)の単体検定。
#   src と同じコンパイラ設定(../../make.inc)でビルドし、libencflow.a を
#   リンクする。実行は ./Run.sh
include ../../make.inc

SRCDIR	= ../../src

all: test_setgv

test_setgv: test_setgv.f90 $(SRCDIR)/libencflow.a
	$(FRT) -o $@ $(FFLAGS) -I$(SRCDIR) test_setgv.f90 $(SRCDIR)/libencflow.a $(LDFLAGS)

$(SRCDIR)/libencflow.a:
	$(MAKE) -C $(SRCDIR)

clean:
	rm -f test_setgv *.o *.mod

.PHONY: all clean
