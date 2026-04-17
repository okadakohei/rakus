# phase_config.md — 資産フェーズ設定
最終更新: 2025-01-01

## 現在のフェーズ: Seed(〜300 万円)

## フェーズ定義と移行ルール

### Seed フェーズ(〜300 万円)
- 資金配分: ETF 40% / FX 30% / 暗号資産 30%
- リスク上限: 1 トレード 15%
- 税務方針: 個人申告、確定申告を自前で実施
- 移行閾値: total_value >= 3,000,000 円

### Growth フェーズ(300 万〜1000 万円)
- 資金配分: ETF 45% / FX 30% / 暗号資産 25%(暗号資産比率を下げる)
- リスク上限: 1 トレード 12%
- 税務方針: 税理士への相談を開始
- 移行閾値: total_value >= 10,000,000 円

### Scale フェーズ(1000 万〜3000 万円)
- 資金配分: ETF 50% / FX 30% / 暗号資産 20%
- リスク上限: 1 トレード 10%
- 税務方針: 税理士関与・法人化の実施を検討
- 移行閾値: total_value >= 30,000,000 円

### Mature フェーズ(3000 万円超)
- 資金配分: ETF 60% / FX 25% / 暗号資産 15%
- リスク上限: 1 トレード 8%(資産防衛優先)
- 税務方針: 法人化・税務顧問常駐
- 移行閾値: なし(最終フェーズ)

## フェーズ移行時の手順(morning.py がアラート → 人間が実施)

1. `morning.py` が `portfolio.json` の `total_value` と移行閾値を毎日比較してアラート出力
2. オーナーが `state/annual_human_review.md` の資産フェーズ欄を更新
3. このファイル(phase_config.md)の「現在のフェーズ」を手動更新
4. `CLAUDE.md` の資金配分・リスク上限セクションを新フェーズの値に手動更新
5. `reviews/phase_transitions.md` に移行記録を追記
6. `tools/backup.py` を手動実行してコミット

## バックアップ取引所への切り替え手順

### ZAIF → Bitbank
1. `.env` の `CRYPTO_EXCHANGE=zaif` を `CRYPTO_EXCHANGE=bitbank` に変更
2. Bitbank の API キーを `BITBANK_API_KEY` / `BITBANK_API_SECRET` に設定
3. ペーパーモードで 3 日間動作確認後に切り替え完了

### OANDA → GMO クリック FX
1. `.env` の `FX_BROKER=oanda` を `FX_BROKER=gmo` に変更
2. GMO のデモ口座で 3 日間確認後に本番切り替え
