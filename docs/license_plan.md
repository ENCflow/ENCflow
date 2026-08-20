# ライセンス確定日の実施計画(Apache-2.0)

内部文書(開発者向け)。
**進捗(2026-08-20)**: 職場承認が下り、§1〜§2 は実施済み
(Apache-2.0 設置完了)。**残りは §3 のみ**で、着手条件は
「共同開発者(風間)の著者掲載の確認」— CITATION.cff の著者 2 名化
(多田・風間、所属付き。可能なら ORCID も)を §3 の手順 3 と同時に
行い、その後に v1.0.0・Zenodo DOI へ進む(DOI で著者名が恒久化される
ため確認が先)。README の開発体制はラボ 2 行表記で確定済み。

前提(developer.md §34.3): 著作権者は個人名(Tsuyoshi Tada)、
ライセンスは Apache License 2.0。2026-08-14 に作成した Apache 一式の
コミットは公開時の履歴再作成で失われたため(2026-08-19 確認)、
revert ではなく本計画で**新規に設置**する。

## 0. 実行前にユーザーが確認しておくこと(§1〜§2 分は完了)

- [x] 職場承認(2026-08-20 取得。個人名・Apache-2.0)
      (著作権表示の年の範囲は **2020-2026** で確定済み 2026-08-19)
- [ ] Zenodo アカウントの用意(GitHub でログイン可)
- [ ] (推奨・任意)org owner の複数化

## 1. ライセンス一式の設置(1 コミット)

- `LICENSE`: Apache-2.0 の正文を**逐語**で設置
  (https://www.apache.org/licenses/LICENSE-2.0.txt をそのまま保存)
- `NOTICE`(新設):

  ```
  ENCflow
  Copyright 2020-2026 Tsuyoshi Tada

  Licensed under the Apache License, Version 2.0.

  If you use ENCflow in your research, please cite the article
  listed in CITATION.cff.
  ```

- `CITATION.cff`: `license: Apache-2.0` を追記(version 更新は §3 で)
- ソース各ファイルへのヘッダ付与は**行わない**(§34.3 の決定どおり)

## 2. 文書の差し替え(同じコミットに含めてよい)

**README.md ライセンス節**(現行の「検討中・全権利留保」を置換):

> ## ライセンス
>
> [Apache License 2.0](LICENSE) です。商用利用・改変・再配布が可能です
> (著作権表示と [NOTICE](NOTICE) の保持が条件。詳細は LICENSE 参照)。
> 研究利用の引用方法は [CITATION.cff](CITATION.cff) を参照してください。

**README.en.md License 節**:

> ## License
>
> [Apache License 2.0](LICENSE). Commercial use, modification, and
> redistribution are permitted (retaining the copyright notice and
> [NOTICE](NOTICE); see LICENSE for details).
> For citation in research, see [CITATION.cff](CITATION.cff).

**README「選ぶ理由」の全ソース公開の項**: 「著作権はクリーンで、
第三者の著作物を含みません」の後に「Apache-2.0 で**商用利用も可能**です」
を追記(日英)。

**CONTRIBUTING.md「コードのプルリクエストについて」節を置換**
(方針決定 2026-08-19: 運用が安定するまで PR は引き続き受け付けない。
理由を「ライセンス未確定」から「品質保証の運用」に差し替える):

> ## コードのプルリクエストについて(当面は受け付けていません)
>
> ENCflow の変更は、回帰基準とのビット一致検証を一つずつ通す
> 運用で品質を保っています。この検証を伴うレビュー体制が外部
> 貢献に対して安定して回せるようになるまで、コードのプル
> リクエストは受け付けていません。コードに関する指摘・提案は
> Issues でいただければ、開発チームが実装します(提案者として
> クレジットします)。
>
> なお Apache-2.0 のもとで**フォークして改変することは完全に
> 自由**です。フォークでの成果や知見も Issues や Discussions で
> 教えていただければ歓迎します。

(CONTRIBUTING.en.md も同旨で置換。受け入れ開始時は Apache
License 2.0 第 5 条のコントリビューション自動ライセンスに基づく
運用とし、その時点でこの節を再度書き換える)

**developer.md**: §34.3 を「確定・設置済み(日付)」に更新。

## 3. v1.0.0 リリースと Zenodo DOI

1. 上記コミットを push → CI 緑を確認
2. **Zenodo 連携を先に ON**: zenodo.org → GitHub(Settings →
   GitHub)→ ENCflow/ENCflow のスイッチを ON(以後の Release が自動で
   アーカイブ+DOI 付与される。スイッチ ON 前のリリースには付かない)
3. CITATION.cff の `version: "1.0.0"` / `date-released` を更新して
   コミット・push(§34.4 の規約: タグを打つコミットに含める)
4. GitHub Releases → Create a new release → タグ `v1.0.0`(on
   publish)→ Target: main → リリースノートを書いて Publish
   (タグ push はこの環境からは 403 のため Release UI で作る)
5. Zenodo に DOI が発行されたことを確認(数分)。**Concept DOI**
   (全版共通)と版 DOI の 2 つができる
6. README(日英)に DOI バッジ+「版を特定した引用が可能」の一文、
   CITATION.cff に `doi:`(Concept DOI)を追記してコミット・push

## 4. 告知(任意)

Discussions(Announcements)に一言:

> ENCflow を Apache License 2.0 で公開しました。商用利用を含め、
> どなたでも自由に利用・改変・再配布できます。あわせて v1.0.0 を
> リリースし、Zenodo で DOI を付与しました(引用方法は README 参照)。
> コードのプルリクエストは運用が安定するまで引き続き受け付けて
> いませんが、指摘・提案は Issues へ、質問・相談は Discussions へ
> どうぞ(CONTRIBUTING 参照)。

## 5. 実施後の消し込み

- handoff.md の「ライセンス確定後の README 追記」項を削除
- 本文書を削除(記録は developer.md §34.3/§34.4 に残す)
