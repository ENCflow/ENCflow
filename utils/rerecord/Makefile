# ENCflow/utils/rerecord/Makefile
#   src のモジュール(libencflow.a と .mod)を利用するユーティリティ
TOPDIR	= ../..
include $(TOPDIR)/make.inc

BINDIR	= $(TOPDIR)/bin

SRCDIR	= $(TOPDIR)/src
LIB	= $(SRCDIR)/libencflow.a

all: rerecord

# ライブラリ形式なので必要な .o はリンカが自動抽出する
# (旧 Makefile の OBJS_rerec のような手動列挙は不要)
rerecord: rerecord.o $(LIB)
	$(FRT) -o $@ $(FFLAGS) $(LDFLAGS) rerecord.o $(LIB)

# .mod ファイルは src 側にあるので -I で参照
rerecord.o: rerecord.f90 $(LIB)
	$(FRT) -c $(FFLAGS) -I$(SRCDIR) rerecord.f90

# src 側が未ビルド・更新済みの場合は先に再ビルドする
$(LIB): FORCE
	$(MAKE) -C $(SRCDIR) libencflow.a

FORCE:

clean:
	rm -f rerecord *.o *.mod

install: rerecord
	mkdir -p $(BINDIR)
	cp -f rerecord $(BINDIR)

.PHONY: all clean install FORCE
