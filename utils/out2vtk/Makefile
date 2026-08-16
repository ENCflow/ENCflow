# ENCflow/utils/out2vtk/Makefile
#   src のモジュール(libencflow.a と .mod)を利用するユーティリティ
TOPDIR	= ../..
include $(TOPDIR)/make.inc

BINDIR	= $(TOPDIR)/bin

SRCDIR	= $(TOPDIR)/src
LIB	= $(SRCDIR)/libencflow.a

all: out2vtk

# ライブラリ形式なので必要な .o はリンカが自動抽出する
out2vtk: out2vtk.o $(LIB)
	$(FRT) -o $@ $(FFLAGS) out2vtk.o $(LIB) $(LDFLAGS)

# .mod ファイルは src 側にあるので -I で参照
out2vtk.o: out2vtk.f90 $(LIB)
	$(FRT) -c $(FFLAGS) -I$(SRCDIR) out2vtk.f90

# src 側が未ビルド・更新済みの場合は先に再ビルドする
$(LIB): FORCE
	$(MAKE) -C $(SRCDIR) libencflow.a

FORCE:

clean:
	rm -f out2vtk *.o *.mod

install: out2vtk
	mkdir -p $(BINDIR)
	cp -f out2vtk $(BINDIR)

.PHONY: all clean install FORCE
