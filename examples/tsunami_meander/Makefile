# ENCflow/examples/tsunami_meander/Makefile
#   make          ../../bin/ の実行ファイルへのリンクと入力(make_init.py が 2 cm 格子の入力を作る)
#   make run      既定の 7 構成(蛇行度 1.10 の水路の 3 構成、直線水路と蛇行度 1.25 の水路の各 2 構成)を順に計算する
#   make sens     感度の 12 構成(砕波スイッチ・初期の段差をなだらかにした計算・砕波段波の非静水圧・エッジ水深・
#                 水路を 30° 回した配置・格子間隔)を計算する
#   make figs     図と数表(plot_results.py。日英)
#   make clean    リンクと生成物を削除する(data_kobayashi/ は残す)
# data_kobayashi/ は論文の PDF から extract_figs.py で読み取った実験値(PDF が要るのはその読み取りだけ。README)

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
RUNS	= bk_h ub_h ub_nh str_h str_nh s125_h s125_nh
SENS	= str_nhb str_nhb2 str_nh_s str_nhb_s bk_nh bk_h_c1 bk_h_r30 ub_nh_r30 bk_h_d4 ub_nh_d4 bk_h_d1 ub_nh_d1
INPUTS	= geoinfo_s110.txt geoinfo_s125.txt geoinfo_str.txt

all: links inputs

inputs: $(INPUTS)

$(INPUTS): make_init.py
	python3 make_init.py

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

# 画面出力は Screen_<構成名>.log(非静水圧の反復回数などが末尾に出る)
run: all
	@for r in $(RUNS); do \
	    echo "== param_$$r.txt"; ./encflow param_$$r.txt > Screen_$$r.log 2>&1 || exit 1; tail -n 1 Screen_$$r.log; \
	done

# 感度の構成の入力と param(wrk_param_*.txt)は、既定の入力・param から作る。
#   str_nhb    直線水路の波状段波、非静水圧 + 砕波スイッチ(既定の判定と縁)
#   str_nhb2   同、砕波スイッチの縁を 2 セルに狭める
#   str_nh_s   直線水路の波状段波、非静水圧(砕波スイッチなし)。初期水位の段差を tanh(s / 0.3 m) のなだらかな水面にする
#              (水面勾配の最大が 0.23 で、砕波スイッチの判定 0.3 に掛からない)
#   str_nhb_s  同、砕波スイッチ(既定の判定と縁)つき
#   bk_nh      砕波段波、非静水圧(砕波スイッチなし)
#   bk_h_c1    砕波段波、静水圧、エッジ水深は既定(f_hcap_upwind = 1)
#   *_r30      格子に対して水路を 30° 回した配置
#   *_d4       4 cm 格子(dt は 2 倍)
#   *_d1       1 cm 格子(dt は半分。第 1 湾曲部を過ぎる 3.7 s まで)
sens: all
	python3 make_init.py --channels str --smooth 0.3 --suffix _s
	python3 make_init.py --channels s110 --rot 30 --suffix _r30
	python3 make_init.py --channels s110 --dx 0.04 --suffix _d4
	python3 make_init.py --channels s110 --dx 0.01 --suffix _d1
	sed -e "s/result_str_nh/result_str_nhb/" \
	    -e "s/^  f_nonhydrostatic = 1.*/  f_nonhydrostatic = 1\n  f_nh_breaking = 1\n  f_hcap_upwind = 2/" \
	    param_str_nh.txt > wrk_param_str_nhb.txt
	sed -e "s/result_str_nh/result_str_nhb2/" \
	    -e "s/^  f_nonhydrostatic = 1.*/  f_nonhydrostatic = 1\n  f_nh_breaking = 1\n  nh_break_margin = 2\n  f_hcap_upwind = 2/" \
	    param_str_nh.txt > wrk_param_str_nhb2.txt
	sed -e "s/_str/_str_s/g" -e "s/result_str_s_nh/result_str_nh_s/" param_str_nh.txt > wrk_param_str_nh_s.txt
	sed -e "s/_str/_str_s/g" -e "s/result_str_s_nh/result_str_nhb_s/" \
	    -e "s/^  f_nonhydrostatic = 1.*/  f_nonhydrostatic = 1\n  f_nh_breaking = 1\n  f_hcap_upwind = 2/" \
	    param_str_nh.txt > wrk_param_str_nhb_s.txt
	sed -e "s/result_ub_nh/result_bk_nh/" -e "s/initial_s110_ub/initial_s110_bk/" param_ub_nh.txt > wrk_param_bk_nh.txt
	sed -e "s/result_bk_h/result_bk_h_c1/" -e "s/^  f_hcap_upwind = 2 .*/  f_hcap_upwind = 1/" param_bk_h.txt > wrk_param_bk_h_c1.txt
	@for r in bk_h ub_nh; do \
	    sed -e "s/_s110/_s110_r30/g" -e "s/result_$$r/result_$${r}_r30/" param_$$r.txt > wrk_param_$${r}_r30.txt; \
	    sed -e "s/_s110/_s110_d4/g" -e "s/dt = 0.002 /dt = 0.004 /" -e "s/result_$$r/result_$${r}_d4/" param_$$r.txt > wrk_param_$${r}_d4.txt; \
	    sed -e "s/_s110/_s110_d1/g" -e "s/dt = 0.002 /dt = 0.001 /" -e "s/tt = 6.5 /tt = 3.7 /" -e "s/result_$$r/result_$${r}_d1/" \
	        param_$$r.txt > wrk_param_$${r}_d1.txt; \
	done
	@for r in $(SENS); do \
	    echo "== wrk_param_$$r.txt"; ./encflow wrk_param_$$r.txt > Screen_$$r.log 2>&1 || exit 1; tail -n 1 Screen_$$r.log; \
	done

figs:
	python3 plot_results.py
	python3 plot_results.py en

install: all

clean:
	rm -rf result_* __pycache__
	rm -f encflow encflow_mpi Screen_*.log wrk_*
	rm -f mask_*.txt z_*.txt e_*.txt geoinfo_*.txt initial_*.txt record_*.txt probes_*.csv

.PHONY: all links inputs run sens figs install clean
