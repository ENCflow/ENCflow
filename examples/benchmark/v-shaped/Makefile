# ENCflow/examples/benchmark/v-shaped/Makefile
#   make          ../../../bin/ の実行ファイルへのリンクと、全格子の入力・全ケースの設定(make_inputs.py)、
#                 理論解 data/analytic.csv(analytic.py)を作る
#   make run      全 19 ケースを計算する(4 スレッドで 15 分ほど。5 m の 45° が大半)
#   make main     8 近傍の主ケース 6 つだけ計算する
#   make clean    リンクと生成物を削除する
#
#   計算の後:  python3 check.py        理論解との差と水収支の表(主ケースは合否つき)
#              python3 plot_results.py 図 figs/*.png(引数 en で英語版を en/figs/ に)

TOPDIR	= ../../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
GRIDS	= dx20_r0 dx20_r45 dx10_r0 dx10_r45 dx5_r0 dx5_r45
MAIN	= $(GRIDS)
NB4	= $(addsuffix _4nb,$(GRIDS))
GOV	= dx10_r0_dif dx10_r0_kin dx10_r45_dif dx10_r45_kin
OD2	= dx20_r0_od2 dx10_r0_od2 dx5_r0_od2
CASES	= $(MAIN) $(NB4) $(GOV) $(OD2)

all: links inputs data/analytic.csv

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

inputs: data_dx10_r0/z.txt

data_dx10_r0/z.txt: make_inputs.py param.txt
	python3 make_inputs.py

data/analytic.csv: analytic.py make_inputs.py
	python3 analytic.py

# 計算済み(result_<case>/summary.csv がある = 最後まで走った)のケースは飛ばす。設定を変えたら make clean から
run: all
	@for c in $(CASES); do $(MAKE) --no-print-directory result_$$c/summary.csv; done

main: all
	@for c in $(MAIN); do $(MAKE) --no-print-directory result_$$c/summary.csv; done

result_%/summary.csv:
	@if [ "$*" = dx10_r0 ]; then p=param.txt; else p=param_$*.txt; fi; \
	    ./encflow $$p | tee Screen_$*.log

clean:
	rm -rf result_* data_* data
	rm -f encflow encflow_mpi a.out Screen_*.log param_dx*.txt

.PHONY: all links inputs run main clean
