# ENCflow/examples/meander/Makefile
#   make        ../../bin/ の実行ファイルへのリンクと入力(make_init.py が z.txt・h.txt・sd.txt・sd_feed.txt を作る)
#   make run    一定流量の 4 構成(非粘着性・粘着性・粘着性+崩落土塊・容量給砂)を順に計算する
#   make varq   出水と低水を繰り返す 4 構成(流量変動のみ・定着・緩い減水期・定着+浮遊砂)
#   make feed   給砂と定着を組み合わせた 2 構成(容量給砂、浮遊砂の平衡濃度給砂+河床の細粒分の帳簿)
#   make clean  リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
RUN	= cohesive cohesive_slump feed
VARQ	= varq fix fixrec fixsusp
FEED	= fixfeed fixsuspfines

all: links inputs

inputs: z.txt h.txt sd.txt sd_feed.txt

z.txt h.txt sd.txt sd_feed.txt: make_init.py
	@python3 make_init.py z > z.txt && python3 make_init.py h > h.txt && python3 make_init.py sd > sd.txt && python3 make_init.py sdfeed > sd_feed.txt

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

# 画面出力は Screen.log / Screen_<構成>.log(plot_results.py が崩落・侵食・給砂の台帳を読む。
# これらは標準エラーに出る警告の行なので 2>&1 で合わせて記録する)
run: all
	./encflow param.txt 2>&1 | tee Screen.log
	@for c in $(RUN); do ./encflow param_$$c.txt 2>&1 | tee Screen_$$c.log; done

varq: all
	@for c in $(VARQ); do ./encflow param_$$c.txt 2>&1 | tee Screen_$$c.log; done

feed: all
	@for c in $(FEED); do ./encflow param_$$c.txt 2>&1 | tee Screen_$$c.log; done

install: all

clean:
	rm -rf result result_* save save_* __pycache__
	rm -f encflow encflow_mpi a.out Screen.log Screen_*.log z.txt h.txt sd.txt sd_feed.txt

.PHONY: all links inputs run varq feed install clean
