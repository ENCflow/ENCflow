# ENCflow/utils/river_flowline/Makefile
#   src のモジュール(libencflow.a と .mod)を利用するユーティリティ
TOPDIR	= ../..
include $(TOPDIR)/make.inc

BINDIR	= $(TOPDIR)/bin

SRCDIR	= $(TOPDIR)/src
LIB	= $(SRCDIR)/libencflow.a

all: river_flowline

# ライブラリ形式なので必要な .o はリンカが自動抽出する
river_flowline: river_flowline.o $(LIB)
	$(FRT) -o $@ $(FFLAGS) river_flowline.o $(LIB) $(LDFLAGS)

# .mod ファイルは src 側にあるので -I で参照
river_flowline.o: river_flowline.f90 $(LIB)
	$(FRT) -c $(FFLAGS) -I$(SRCDIR) river_flowline.f90

# src 側が未ビルド・更新済みの場合は先に再ビルドする
$(LIB): FORCE
	$(MAKE) -C $(SRCDIR) libencflow.a

FORCE:

clean:
	rm -f river_flowline *.o *.mod

install: river_flowline
	mkdir -p $(BINDIR)
	cp -f river_flowline $(BINDIR)

.PHONY: all clean install FORCE
