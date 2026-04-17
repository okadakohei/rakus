# CLAUDE.md — 自律型トレーディングエージェント憲法
最終更新: 2025-01-01

## 1. 基本設定

| 項目 | 値 |
|------|-----|
| 元手 | 1,000,000 円 |
| 運用モード | PAPER（実弾化時 LIVE へ変更） |
| 運用期間目標 | 10 年 |
| リスク上限 | 1 トレード 15% まで |
| キャッシュ留保 | なし（フル投資） |

### 資金配分
- 米国株 ETF（SPY/QQQ）: 400,000 円
- FX USD/JPY（OANDA）:   300,000 円
- 暗号資産 BTC/JPY（ZAIF）: 300,000 円

## 2. 絶対禁止事項（変更不可）

1. **インサイダー防止**: FRD Japan・水産養殖セクター関連は一切取引しない
2. **PAPER モード中は実際の発注 API を呼ばない**
3. 連敗 5 回で強制反省モード（取引継続可だが必ず原因分析を記録）
4. 全資産が元手の 10% 以下になったら全滅時プロトコルを実行

## 3. 市場と税制

| 市場 | API | 税制 | 実効税率 | 損失繰越 |
|------|-----|------|---------|---------|
| 米国株 ETF（SPY/QQQ） | yfinance（無料） | 申告分離 | 20% | 3 年可 |
| FX USD/JPY（OANDA） | OANDA REST API | 申告分離 | 20% | 3 年可 |
| 暗号資産 BTC/JPY（ZAIF） | ZAIF API | 総合課税 | 43% | 不可 |

- 暗号資産は税率が高いため、利益目標を FX/ETF の 1.4 倍以上に設定
- 年間利益 20 万円ラインに近づいたらポジション縮小

### バックアップ取引所
- ZAIF が障害時 → Bitbank または bitFlyer へ切り替え
  - 切り替え手順: `state/phase_config.md` の「バックアップ切替手順」参照
- OANDA が障害時 → GMO クリック FX へ切り替え

## 4. 毎日のルーティン

```
09:00 JST  morning.py   — 市場データ取得・ニュース収集・ファクトチェック・シグナル判断・発注・全滅チェック
22:00 JST  reflection.py — 1 日の振り返り・スコアリング・state 更新
23:00 JST  backup.py    — GitHub 自動バックアップ
```

### 月次タスク（毎月 1 日）
- `tools/regulation_check.py` を実行して税制・法規制変更を確認（morning.py が自動実行）
- `state/source_profiles.md` の情報源プロファイルを更新（手動）
- `state/ai_behavior_log.md` のパターン信頼度を再評価（手動）

### 12 月の特別タスク
- 毎日: `morning.py` が損出し候補を `daily/reports/tax_loss_MMDD.json` に自動出力
- 12/31: `daily/year_end.py` を実行して `annual_report_YYYY.json` を生成

### 年次タスク（毎年 1 月）
- `state/annual_human_review.md` を開いてオーナーが手動更新
- 給与・家族構成・リスク許容度・資産フェーズ・インサイダー規制対象を確認

## 5. AI Meta-Strategy（群れ対策）

世界中で同じ AI トレーダーが稼働している前提で、群れの反応を予測して逆用する。

- 5 分以内に 3% 超の急変動 → AI 過剰反応疑いで逆張りを検討
- 有名指標（RSI/MA 等）はシグナル直前を狙う（クラウド・フロントランニング）
- パターンは `state/ai_behavior_log.md` に蓄積して精度を上げる

## 6. 情報源管理

Tier 定義:
- **Tier1**: 公式発表（FRB・日銀・取引所等）— 最高信頼
- **Tier2**: 主要メディア（Reuters/Bloomberg 等）
- **Tier3**: 個人ブログ・アナリスト予測
- **Tier4**: SNS・匿名情報

発信者プロファイルは `state/source_profiles.md` で管理。
バイアス・利益相反・誇張度・実績スコアを記録し、思想部分を除去して事実のみ抽出。

## 7. 資産フェーズ管理

詳細は `state/phase_config.md` を参照。

| フェーズ | 資産額 | 主な変更点 |
|---------|-------|----------|
| Seed | ～300 万円 | 現在のデフォルト設定 |
| Growth | 300 万～1000 万円 | 法人化検討・戦略多様化 |
| Scale | 1000 万～3000 万円 | 税理士関与・ヘッジ導入 |
| Mature | 3000 万円超 | 資産防衛優先・分散強化 |

フェーズ移行は `morning.py` が `portfolio.json` の `total_value` を監視し、
閾値超過時にアラートを出力する。移行手順は `state/phase_config.md` を参照。

## 8. GitHub バックアップ

- 毎日 23:00 JST に `tools/backup.py` を実行
- state/ と daily/reports/ と CLAUDE.md を自動コミット・プッシュ

## 9. 全滅時プロトコル

資産が元手の 10%（100,000 円）以下になったら `morning.py` が自動検知して:
1. 全ポジションをクローズ（PAPER モード中は記録のみ）
2. `daily/reports/wipeout_YYYYMMDD.json` に原因分析テンプレートを生成
3. `state/ai_behavior_log.md` に教訓セクションを追記
4. `state/strategy.md` の改訂を促すアラートを出力
5. 環境変数 `NOTIFY_EMAIL` 宛にメール通知
6. オーナーの手動承認（`portfolio.json` の `wipeout_acknowledged: true` を設定）後にリスタート
