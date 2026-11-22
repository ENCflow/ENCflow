## 公開準備(方針の正本は developer.md §34)

- 到達点: v3.0.0(2026-10-25。タグ v3.0.0 = 1aaf1752。Zenodo の版 DOI
  10.5281/zenodo.23635011)。CSDMS モデルリポジトリへ提出済み(2026-10-29。控えは
  docs/csdms_registration.md)。GitHub の「Cite this repository」の表示、Organization の
  owner の複数化も確認済み(2026-10-29)。リリースの記録は developer.md §34.4。
- 残り(任意・利用者の操作): Discussions への告知投稿。
- 注釈付きタグ: Claude Code の cloud 環境からは refs/tags の push が HTTP 403 で拒否される
  ため、これまでのタグは Release UI で作った軽量タグ(§34.4 の実態の注記)。§34.4 の
  「注釈付き」は、ローカルからタグを push できる資格情報を整えてから次のリリースで適用する。
- **実行時メッセージの英語化収斂**(触ったファイルから順に。
  Log 比較対象の文字列に触れる場合は reference への影響に注意)。
- 国際化(developer.md §34.2、docs/multilingual.md)の残り: (e) 接尾辞方式(test/README.en.md
  等 5 件)の en/ への移行は任意(規約 §2・§5)。コード内コメントの言語方針は海外コア
  開発者が現実になった時点で §34.2 を改定して決定(それまで日本語のまま)。未確認
  (unreviewed)のミラーは 0 を保ち、正本を変えたら同じ作業で訳を更新する(CI の stale
  検出に従う)。
