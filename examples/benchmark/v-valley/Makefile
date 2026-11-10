# ENCflow/examples/benchmark/v-valley/Makefile
#   make          ../../../bin/ の実行ファイルへのリンクと、全格子の入力・全ケースの設定(make_inputs.py)を作る
#   make run      全 19 ケースを計算する(4 スレッドで 10 分ほど。5 m の 45° が大半)
#   make clean    リンクと生成物を削除する
#
#   計算の後:  python3 check.py        0° との差・疑似窪地の貯留・水収支の表
#              python3 plot_results.py 図 figs/*.png(引数 en で英語版を en/figs/ に)

TOPDIR	= ../../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
SLOPES	= s01 s02 s03 s04
CASES	= $(foreach s,$(SLOPES),$(s)_dx10_r0 $(s)_dx10_r45 $(s)_dx10_r45_4nb) s03_dx10_r0_4nb \
	  $(foreach d,dx20 dx5,s03_$(d)_r0 s03_$(d)_r45 s03_$(d)_r45_4nb)

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

inputs: data_s03_dx10_r0/z.txt

data_s03_dx10_r0/z.txt: make_inputs.py param.txt
	python3 make_inputs.py

# 計算済み(result_<case>/summary.csv がある = 最後まで走った)のケースは飛ばす。設定を変えたら make clean から
run: all
	@for c in $(CASES); do $(MAKE) --no-print-directory result_$$c/summary.csv; done

result_%/summary.csv:
	@if [ "$*" = s03_dx10_r0 ]; then p=param.txt; else p=param_$*.txt; fi; \
	    ./encflow $$p | tee Screen_$*.log

clean:
	rm -rf result_* data_*
	rm -f encflow encflow_mpi a.out Screen_*.log param_s*.txt

.PHONY: all links inputs run clean
