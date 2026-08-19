# =====================================================================
# ENCflow トップレベル Makefile
#   src と utils 以下を一括で make / make install / make clean する。
#
#   使い方(ENCflow 直下で):
#     make            srcとutilsディレクトリをビルド
#     make install    実行ファイルを $(BINDIR) にコピー
#     make clean      全ディレクトリの生成物を削除
#     make cleanref   回帰テスト用結果を削除
#     make src        特定ディレクトリだけビルドすることも可能
#     make utils/rerecord
# =====================================================================

# ビルド対象ディレクトリ
#   src を先頭に置くこと(utils/rerecord 等が src の libencflow.a に
#   依存するため。各 Makefile 側でも再帰的に src をビルドするので
#   順序が崩れても壊れはしないが、先に src を済ませる方が効率的)
SUBDIRS	= src \
	  utils/calc_catchmentarea \
	  utils/lu2mask \
	  utils/modify_elevation \
	  utils/modify_river \
	  utils/modify_sealand \
	  utils/out2vtk \
	  utils/prep_flux_transect \
	  utils/rerecord \
	  utils/rmdepress_river

# テスト用ディレクトリ
TESTDIRS	= test/chichibu test/wave

# install 対象(install ターゲットを持つディレクトリのみ列挙)
#   他の utils ユーティリティにも install を追加したらここに足す
#INSTALLDIRS	= src \
#	  utils/rerecord \
#	  utils/rmdepress_river
INSTALLDIRS	= $(SUBDIRS) $(TESTDIRS)

# 実行ファイルのインストール先
BINDIR	= bin

# サンプルデータディレクトリ
SMPLDIRS	= \
		  examples/benchmark/h-plane \
		  examples/benchmark/v-shaped \
		  examples/benchmark/v-valley

all: $(SUBDIRS)

# 各ディレクトリ名をそのままターゲットにする
#   例: make src / make utils/rerecord
$(SUBDIRS):
	$(MAKE) -C $@

# utils/lu2mask, utils/out2vtk, utils/rerecord, utils/rmdepress_river は
# src の成果物に依存
utils/lu2mask utils/out2vtk utils/rerecord utils/rmdepress_river: src


install: all
	mkdir -p $(BINDIR)
	@for d in $(INSTALLDIRS); do \
		$(MAKE) -C $$d install || exit 1; \
	done

clean:
	@for d in $(SUBDIRS); do \
		$(MAKE) -C $$d clean || exit 1; \
	done
	rm -rf $(BINDIR)
	@for d in $(TESTDIRS); do \
		$(MAKE) -C $$d clean || exit 1; \
	done
	@for d in $(SMPLDIRS); do \
		$(MAKE) -C $$d clean || exit 1; \
	done

cleanref:
	@for d in $(TESTDIRS); do \
		$(MAKE) -C $$d cleanref || exit 1; \
	done

.PHONY: all install clean cleanref $(SUBDIRS)
