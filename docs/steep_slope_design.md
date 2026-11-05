# 急勾配の重力補正の解説(移動しました)

<!-- i18n-redirect -->

この文書の内容は、2026-11-05 にユーザーガイドの解説
[急勾配の重力補正の解説](users_guide/steep_slope.md)(英語版
[Steep-slope gravity correction](en/users_guide/steep_slope.md))へ移しました。最終的な実装
(既定の `f_gravity_correction = 2`)の説明書として書き直し、設計の議論(今後の課題の選択肢 A〜F と
推奨の順序)は削りました。

- 判断の経緯と検証の記録: [developer.md](developer.md) §91・§93
- 残る課題(混合体流動の抵抗則、急な地盤の上の深い水、圧力の項の係数、水の流れの曲率など):
  [handoff.md](handoff.md) 00l
- 移す前の本文: git の履歴(2026-11-05 の書き換えより前の版)
