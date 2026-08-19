# ライセンス確定日の実施計画(Apache-2.0)

内部文書(開発者向け)。**本文書はライセンスの宣言ではない**。リポジトリは
確定作業の完了まで全権利留保のまま(README のライセンス節が正本)。
職場の正式確認が取れた日に、この手順を上から順に実行する。

前提(developer.md §34.3): 著作権者は個人名(Tsuyoshi Tada)、
ライセンスは Apache License 2.0。2026-08-14 に作成した Apache 一式の
コミットは公開時の履歴再作成で失われたため(2026-08-19 確認)、
revert ではなく本計画で**新規に設置**する。

## 0. 実行前にユーザーが確認しておくこと

- [ ] 職場承認の文言と、著作権表示の**年の範囲**(下書きの `20XX` を
      開発開始年に置換)
- [ ] Zenodo アカウントの用意(GitHub でログイン可)
- [ ] (推奨・任意)org owner の複数化

## 1. ライセンス一式の設置(1 コミット)

- `LICENSE`: Apache-2.0 の正文を**逐語**で設置
  (https://www.apache.org/licenses/LICENSE-2.0.txt をそのまま保存)
- `NOTICE`(新設):

  ```
  ENCflow
  Copyright 20XX-2026 Tsuyoshi Tada

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

**CONTRIBUTING.md「コードのプルリクエストについて」節を置換**:

> ## コードのプルリクエスト(受け付けます)
>
> Apache-2.0 の確定に伴い、コードのプルリクエストを受け付けます。
> 提出されたコントリビューションは Apache License 2.0 第 5 条に
> 基づき同ライセンスで提供されたものとして扱います(別段の合意が
> ない限り)。大きな変更は、実装前に Issue または Discussions で
> 方針を相談してください(設計判断の正本は docs/developer.md)。
> 検証規律(回帰基準・ビット再現)は CLAUDE.md を参照してください。

(CONTRIBUTING.en.md も同旨で置換。「ライセンス確定まで不受理」の
段落と、README の CONTRIBUTING 参照文中の「コード PR の現行方針」の
言い回しは不要になるので合わせて調整)

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
> コードのプルリクエストの受け付けも開始します(CONTRIBUTING 参照)。

## 5. 実施後の消し込み

- handoff.md の「ライセンス確定後の README 追記」項を削除
- 本文書を削除(記録は developer.md §34.3/§34.4 に残す)
