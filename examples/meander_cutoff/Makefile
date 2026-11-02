# ENCflow/examples/meander_cutoff/Makefile
#   make          ../../bin/ の実行ファイルへのリンクと入力(make_init.py が z.txt・h.txt・sd.txt を作る。約 10 秒)
#   make run      出水ありの 2 構成(安息角のみ・崩落土塊あり。地形 30 h)を順に計算する
#   make noflood  出水なしの 4 構成(対照・崩落土塊・粘着性+崩落土塊・同+細粒分。地形 180 h)を順に計算する
#   make clean    リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
NOFLOOD	= noflood slump_noflood slump_cohesive slump_fines

all: links inputs

inputs: z.txt h.txt sd.txt

z.txt h.txt sd.txt: make_init.py
	@python3 make_init.py z > z.txt && python3 make_init.py h > h.txt && python3 make_init.py sd > sd.txt

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

# 画面出力は Screen.log / Screen_<構成>.log(plot_results.py が崩落・細粒分の台帳を読む。
# これらは標準エラーに出る警告の行なので 2>&1 で合わせて記録する)
run: all
	./encflow param.txt 2>&1 | tee Screen.log
	./encflow param_slump.txt 2>&1 | tee Screen_slump.log

noflood: all
	@for c in $(NOFLOOD); do ./encflow param_$$c.txt 2>&1 | tee Screen_$$c.log; done

install: all

clean:
	rm -rf result result_* save save_* __pycache__
	rm -f encflow encflow_mpi a.out Screen.log Screen_*.log z.txt h.txt sd.txt

.PHONY: all links inputs run noflood install clean
