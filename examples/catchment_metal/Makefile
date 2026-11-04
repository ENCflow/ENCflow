# ENCflow/examples/catchment_metal/Makefile
#   make          ../../bin/ の実行ファイルへのリンクと入力(data/。gen_data.py)を作る
#   make run      7 ケースを順に計算する(4 スレッドで 1 ケース 15〜20 分。計 2 時間 15 分前後)
#   make step3    1 ケースだけ計算する(step1〜step6、step5_notank)
#   make clean
TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
CASES	= step1 step2 step3 step4 step5 step5_notank step6

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

inputs: data/cells.txt

data/cells.txt: gen_data.py
	python3 gen_data.py

run: all
	@for c in $(CASES); do ./encflow param_$$c.txt | tee Screen_$$c.log; done

$(CASES): all
	./encflow param_$@.txt | tee Screen_$@.log

clean:
	rm -rf data $(addprefix result_,$(CASES))
	rm -f encflow encflow_mpi a.out Screen*.log

.PHONY: all links inputs run clean $(CASES)
