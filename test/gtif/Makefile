# ENCflow/test/gtif/Makefile
#   GeoTIFF リーダーの回帰テスト。src と同じコンパイラ設定(../../make.inc)
#   でビルドし、libencflow.a(m_geotiff を含む)をリンクする。
#   実行は ./Run.sh
include ../../make.inc

SRCDIR	= ../../src

all: test_gtif_reader

test_gtif_reader: test_gtif_reader.f90 $(SRCDIR)/libencflow.a
	$(FRT) -o $@ $(FFLAGS) -I$(SRCDIR) test_gtif_reader.f90 $(SRCDIR)/libencflow.a $(LDFLAGS)

$(SRCDIR)/libencflow.a:
	$(MAKE) -C $(SRCDIR)

clean:
	rm -f test_gtif_reader *.o *.mod

.PHONY: all clean
