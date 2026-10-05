# SHGRAG Task Planı

Kaynaklar:
- **[P]** `tmp/Capstone_Project_Proposal.docx` (capstone isterleri, lokal)
- **[PhD]** `tmp/CFPhD_SHGRAG.pdf` (doktora hedefleri, lokal)
- **[GPT]** ChatGPT konuşması (`docs/chatgpt_conversation_summary.md`)
- **[DONE]** Bu repoda tamamlanan işler

Linear: [SHGRAG projesi](https://linear.app/ffbilsel/project/shgrag-f526f86c3d26). Milestone'lar M0–M3, bağımlılıklar "blocked by" ilişkisi olarak girildi.

Öncelik etiketleri:

| Etiket | Anlamı |
|---|---|
| P0 | Acil / bloklayıcı |
| P1 | Yüksek |
| P2 | Orta |
| P3 | Düşük / uzun vade |

## Çakışmalar ve bağımlılıklar (önce okunmalı)

| # | Çakışma | Etkisi | Karar / sıra |
|---|---|---|---|
| K1 | **Kapsam çakışması.** Proposal gerçek cihaz entegrasyonunu ve otomatik execution'ı kapsam dışı sayıyor. [GPT] ve [PhD] ise abstraction layer, execution ve rollback öneriyor. | M2'deki işlerin yapılıp yapılmayacağı belirsiz | **C1 (hoca ile kapsam maili) M2'deki her işi bloklar.** M1 kapsamdan bağımsız, hemen yürür. |
| K2 | **Dataset dondurma ↔ deney.** Benchmark deneyden sonra değişirse sonuçlar geçersizleşir. | Tekrar maliyeti (API ücreti + zaman) | C3 (ikinci etiketleyici ve public kural uyarlaması) **C5'ten önce** bitmeli. Ardından dataset `v1.0` olarak tag'lenir. |
| K3 | **Novelty çakışması.** KFUPM SHGRAG tezi (2026), CAGE-TAP, SIGFRID ve TAPFixer aynı problemi büyük ölçüde çözmüş. | Makale iddiası zayıflayabilir | C2 (related-work) **C9'dan (makale) ve M2 seçiminden önce** yapılmalı. |
| K4 | **Mükerrer öneriler.** Aynı iş farklı kaynaklarda farklı adlarla geçiyor. | Çift iş | Birleştirildi: E5 = formal doğrulama + LTL/model checking. C7 = robustness + graph kalitesi duyarlılığı. E1 = abstraction layer + rule ingestion. E9 = causal-path açıklama + sertifikalar. |
| K5 | **Temperature kontrolü.** Proposal "aynı temperature" istiyor, ama Claude Opus 5.5 temperature kabul etmiyor. | Tekrarlanabilirlik | Model, effort, prompt ve şema sabit tutuldu. Varyans 3+ run ile ölçülüyor. Bu durum raporda "threats to validity" olarak yer almalı (C9). |
| K6 | **Zaman çakışması.** Dönem planına göre hafta 9–10 deney, 11–12 analiz. M2 işleri bu süreyle yarışıyor. | Capstone teslimi riski | M1 her zaman önce gelir. M2'den en fazla 2–3 iş seçilmeli (önerilen: E5 → E7 → E6). |
| K7 | **Güvenlik çakışması.** Gerçek cihazda execution (E6) riskli. | Fiziksel zarar | E6 yalnızca E5 (deterministik doğrulama) ve E7 (digital twin) sonrası, önce simülasyonda yapılır. |

## M0 — Tamamlananlar [DONE]

| ID | Task | Kaynak |
|---|---|---|
| D1 ([FFB-5](https://linear.app/ffbilsel/issue/FFB-5)) | Benchmark: 20 ev, 98 kural, 75 case (15 logical / 14 semantic / 13 physical / 33 clean), ground truth ve gerekçeler | [P] §5 |
| D2 ([FFB-6](https://linear.app/ffbilsel/issue/FFB-6)) | Scenario şeması ve validasyon (YAML, referans bütünlüğü) | [P] §4 |
| D3 ([FFB-7](https://linear.app/ffbilsel/issue/FFB-7)) | Graph builder (HAS_DEVICE, HAS_STATE, HAS_ENV, TRIGGERED_BY, CONDITIONED_ON, TARGETS, AFFECTS) | [P] §4, [PhD] Obj.1 |
| D4 ([FFB-8](https://linear.app/ffbilsel/issue/FFB-8)) | Retriever: multi-hop AFFECTS zincirleri, touch-point'ler, kompakt metin bağlamı | [P] §4, [PhD] Obj.2 |
| D5 ([FFB-9](https://linear.app/ffbilsel/issue/FFB-9)) | LLM reasoner (Claude, structured output) ve text-only baseline, aynı prompt ve şema | [P] §4 |
| D6 ([FFB-10](https://linear.app/ffbilsel/issue/FFB-10)) | Deterministik symbolic checker (rule-based referans baseline) | [PhD] Obj.4 |
| D7 ([FFB-11](https://linear.app/ffbilsel/issue/FFB-11)) | Değerlendirme: P/R/F1/Acc, tür bazında recall/F1, FP/FN, ablation, McNemar, stabilite, açıklama proxy'si, uzman 0/1 sayfası | [P] §5, §7 |
| D8 ([FFB-12](https://linear.app/ffbilsel/issue/FFB-12)) | Testler: functional, direct-conflict, hidden-dependency, clean-case, ablation, pipeline (61 test) | [P] §6 |
| D9 ([FFB-13](https://linear.app/ffbilsel/issue/FFB-13)) | Streamlit demo, graph görselleri, dokümanlar | [P] §4, §9 |

## M1 — Capstone tamamlama (öncelik sırasıyla)

| Sıra | ID | Task | Öncelik | Bağımlılık | Kaynak |
|---|---|---|---|---|---|
| 1 | C1 ([FFB-14](https://linear.app/ffbilsel/issue/FFB-14)) | Hocaya kapsam mailini gönder; kapsamı ve M2 seçimini netleştir. Fatih Alagöz hocaya güncel bilgi ver. | P0 | — | [GPT] |
| 2 | C2 ([FFB-15](https://linear.app/ffbilsel/issue/FFB-15)) | Related-work analizi: KFUPM SHGRAG tezi baseline olarak; SIGFRID, TAPFixer, IoTSafe, AutoIoT, CAGE-TAP, PhysCheck ile eksen bazlı boşluk analizi | P0 | — | [GPT] §D, §3 |
| 3 | C4 ([FFB-16](https://linear.app/ffbilsel/issue/FFB-16)) | Anthropic API erişimi ve smoke test (`shgrag run --limit 2 --runs 1`) | P0 | — | [P] §5 |
| 4 | C3 ([FFB-17](https://linear.app/ffbilsel/issue/FFB-17)) | Benchmark gözden geçirme: ikinci etiketleyici, IFTTT / SmartThings / HA public örneklerinden uyarlama, dataset `v1.0` dondurma | P1 | — (K2: C5'ten önce) | [P] §5 |
| 5 | C5 ([FFB-18](https://linear.app/ffbilsel/issue/FFB-18)) | Ana deney: 75 case × 3 run × {text, graph, graph_noaffects} + symbolic | P0 | C3, C4 | [P] §5, §6 |
| 6 | C6 ([FFB-19](https://linear.app/ffbilsel/issue/FFB-19)) | Uzman 0/1 değerlendirmesi (açıklama desteklenmiş mi / repair güvenli mi) | P1 | C5 ([FFB-18](https://linear.app/ffbilsel/issue/FFB-18)) | [P] §5, §7 |
| 7 | C7 ([FFB-20](https://linear.app/ffbilsel/issue/FFB-20)) | Hata analizi ve duyarlılık: hata graph eksiğinden mi, LLM'den mi? Prompt wording, model ve graph kalitesi (eksik/yanlış kenar) robustness | P1 | C5 ([FFB-18](https://linear.app/ffbilsel/issue/FFB-18)) | [P] §8, [GPT] B |
| 8 | C8 ([FFB-21](https://linear.app/ffbilsel/issue/FFB-21)) | Plot'lar, tablolar ve demo videosu | P1 | C5, C6 | [P] §9 |
| 9 | C9 ([FFB-22](https://linear.app/ffbilsel/issue/FFB-22)) | Final rapor ve makale taslağı (`docs/report_outline.md`) | P1 | C2, C6, C7 | [P] §9 |

## M2 — Kapsam genişletmeleri (C1 kararına bağlı, önerilen sırayla)

| Sıra | ID | Task | Öncelik | Bağımlılık | Kaynak |
|---|---|---|---|---|---|
| 1 | E5 ([FFB-23](https://linear.app/ffbilsel/issue/FFB-23)) | Deterministik / formal doğrulama katmanı: LLM önerir, verifier doğrular (constraint / LTL + model checking). D6 üzerine kurulur. | P1 | C1 ([FFB-14](https://linear.app/ffbilsel/issue/FFB-14)) | [PhD], [GPT] B, C |
| 2 | E9 ([FFB-24](https://linear.app/ffbilsel/issue/FFB-24)) | Causal-path açıklama ve conflict/repair sertifikaları (D4 zincirleri temel) | P2 | C1 ([FFB-14](https://linear.app/ffbilsel/issue/FFB-14)) | [GPT] A6, D9 |
| 3 | E7 ([FFB-29](https://linear.app/ffbilsel/issue/FFB-29)) | Digital twin / simülatör: graph etkilerini zamanda simüle et, repair'i önce burada dene | P1 | E5 ([FFB-23](https://linear.app/ffbilsel/issue/FFB-23)) | [GPT] A4, D6 |
| 4 | E4 ([FFB-31](https://linear.app/ffbilsel/issue/FFB-31)) | Temporal / causal reasoning: gecikmeli ve zincirleme etkiler, temporal kenarlar | P1 | E7 ([FFB-29](https://linear.app/ffbilsel/issue/FFB-29)) | [GPT] B, D4 |
| 5 | E6 ([FFB-32](https://linear.app/ffbilsel/issue/FFB-32)) | Plan–Approve–Execute–Verify agentic repair (önce simülasyonda) | P1 | E5, E7 (K7) | [PhD] Obj.3, [GPT] A3 |
| 6 | E8 ([FFB-34](https://linear.app/ffbilsel/issue/FFB-34)) | Rollback: post-condition sağlanmazsa konfigürasyonu geri al | P2 | E6 ([FFB-32](https://linear.app/ffbilsel/issue/FFB-32)) | [GPT] D7 |
| 7 | E1 ([FFB-25](https://linear.app/ffbilsel/issue/FFB-25)) | Ortak IoT abstraction katmanı (Home Assistant / MQTT / Matter) ve otomatik kural içe aktarma (HA YAML → TCA) | P1 | C1 ([FFB-14](https://linear.app/ffbilsel/issue/FFB-14)) | [GPT] A1, B |
| 8 | E2 ([FFB-30](https://linear.app/ffbilsel/issue/FFB-30)) | Dinamik knowledge graph: artımlı güncelleme, graph diff | P2 | E1 ([FFB-25](https://linear.app/ffbilsel/issue/FFB-25)) | [GPT] A2, D2 |
| 9 | E3 ([FFB-33](https://linear.app/ffbilsel/issue/FFB-33)) | Runtime conflict tespiti: yeni kural veya state değişiminde etkilenen alt graf üzerinde | P2 | E2 ([FFB-30](https://linear.app/ffbilsel/issue/FFB-30)) | [GPT] A5, D3 |
| 10 | E10 ([FFB-26](https://linear.app/ffbilsel/issue/FFB-26)) | Eksik bilgi / belirsizlik: abstain et veya kullanıcıya sor ("bu priz neyi besliyor?") | P2 | C7 ([FFB-20](https://linear.app/ffbilsel/issue/FFB-20)) | [GPT] B, D10 |
| 11 | E11 ([FFB-27](https://linear.app/ffbilsel/issue/FFB-27)) | Risk / severity skorlama (kapı unlock > ışık) | P3 | C5 ([FFB-18](https://linear.app/ffbilsel/issue/FFB-18)) | [GPT] B |
| 12 | E14 ([FFB-28](https://linear.app/ffbilsel/issue/FFB-28)) | Çok kullanıcılı policy conflict'leri (USER, OWNS, AUTHORIZED_FOR) | P3 | — | [GPT] B |

## M3 — Uzun vade / doktora (P3)

| ID | Task | Kaynak |
|---|---|---|
| L1 ([FFB-35](https://linear.app/ffbilsel/issue/FFB-35)) | Smart building ölçeği (hiyerarşik graph, BMS, binlerce bağımlılık) | [GPT] F |
| L2 ([FFB-36](https://linear.app/ffbilsel/issue/FFB-36)) | Endüstriyel IoT genişlemesi | [GPT] F |
| L3 ([FFB-37](https://linear.app/ffbilsel/issue/FFB-37)) | AI-agent safety middleware: "bu AI ajanının fiziksel aksiyonu güvenli mi?" | [GPT] F, [PhD] |
| L4 ([FFB-38](https://linear.app/ffbilsel/issue/FFB-38)) | Automation GitOps / CI: PR'da conflict raporu, versiyonlama | [GPT] C |
| L5 ([FFB-39](https://linear.app/ffbilsel/issue/FFB-39)) | Safety-invariant mining ve policy hiyerarşisi | [GPT] C |
| L6 ([FFB-40](https://linear.app/ffbilsel/issue/FFB-40)) | Klasik graph algoritmaları: SCC ile osilasyon, centrality ile kritik cihaz, blast-radius | [GPT] C |
| L7 ([FFB-41](https://linear.app/ffbilsel/issue/FFB-41)) | Kullanılabilirlik çalışması ve gerçek çoklu cihaz testbed'inde değerlendirme | [PhD] Obj.4 |
