# =====================================================================
# ENCflow トップレベル Makefile
#   src と misc 以下を一括で make / make install / make clean する。
#
#   使い方(ENCflow 直下で):
#     make            全ディレクトリをビルド
#     make install    実行ファイルを $(BINDIR) にコピー
#     make clean      全ディレクトリの生成物を削除
#     make src        特定ディレクトリだけビルドすることも可能
#     make misc/rerecord
# =====================================================================

# ビルド対象ディレクトリ
#   src を先頭に置くこと(misc/rerecord 等が src の libencflow.a に
#   依存するため。各 Makefile 側でも再帰的に src をビルドするので
#   順序が崩れても壊れはしないが、先に src を済ませる方が効率的)
SUBDIRS	= src \
	  misc/calc_catchmentarea \
	  misc/modify_elevation \
	  misc/modify_river \
	  misc/modify_sealand \
	  misc/prep_flux_transect \
	  misc/rerecord \
	  misc/rmdepress_river

# install 対象(install ターゲットを持つディレクトリのみ列挙)
#   他の misc ユーティリティにも install を追加したらここに足す
#INSTALLDIRS	= src \
#	  misc/rerecord \
#	  misc/rmdepress_river
INSTALLDIRS	= $(SUBDIRS)

# 実行ファイルのインストール先
BINDIR	= bin


all: $(SUBDIRS)

# 各ディレクトリ名をそのままターゲットにする
#   例: make src / make misc/rerecord
$(SUBDIRS):
	$(MAKE) -C $@

# misc/rerecord, misc/rmdepress_river は src の成果物に依存
misc/rerecord misc/rmdepress_river: src


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

.PHONY: all install clean $(SUBDIRS)
