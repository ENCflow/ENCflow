# ENCflow/examples/<case>/Makefile(各ケース共通)
#
#   make        ../../bin/ にある実行ファイル(encflow, encflow_mpi)への
#               シンボリックリンクをここに作る(共存可)。どちらも
#               未ビルドなら src で make install(make.inc の現在の
#               モード)を実行してから作る
#   make clean  リンクと ./result 以下をすべて削除する
#
#   実行は手動で:  ./encflow param_xxx.txt など
#   (MPI 版は mpirun -np N ./encflow_mpi param_xxx.txt)

TOPDIR	= ../../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src

all: links

# シンボリックリンクの作成
#   bin/ に存在する実行ファイルすべてにリンクを張る(常に張り直すので
#   リンク切れも解消される)。実体が消えた側のリンクは削除する。
links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

clean:
	rm -f encflow encflow_mpi a.out
	rm -rf result

.PHONY: all links clean
