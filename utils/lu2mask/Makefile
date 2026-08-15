# ENCflow/utils/lu2mask/Makefile
#   src のモジュール(libencflow.a と .mod)を利用するユーティリティ
TOPDIR	= ../..
include $(TOPDIR)/make.inc

BINDIR	= $(TOPDIR)/bin

SRCDIR	= $(TOPDIR)/src
LIB	= $(SRCDIR)/libencflow.a

all: lu2mask

# ライブラリ形式なので必要な .o はリンカが自動抽出する
lu2mask: lu2mask.o $(LIB)
	$(FRT) -o $@ $(FFLAGS) lu2mask.o $(LIB) $(LDFLAGS)

# .mod ファイルは src 側にあるので -I で参照
lu2mask.o: lu2mask.f90 $(LIB)
	$(FRT) -c $(FFLAGS) -I$(SRCDIR) lu2mask.f90

# src 側が未ビルド・更新済みの場合は先に再ビルドする
$(LIB): FORCE
	$(MAKE) -C $(SRCDIR) libencflow.a

FORCE:

clean:
	rm -f lu2mask *.o *.mod

install: lu2mask
	mkdir -p $(BINDIR)
	cp -f lu2mask $(BINDIR)

.PHONY: all clean install FORCE
