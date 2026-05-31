# stack-skill-creator redesign — lightweight, version-anchored stack skill

> 你的指示:① stack skill 產出**非常輕量**;② implementation pattern 拆成獨立的細粒度
> pattern skill(POC 產物);③ **版本 + 該版本 highlight 是 stack skill 的核心職責**,
> creator 建立時就要抓,記進 convention;④ **拿掉 `Related skills`** —— skill 之間的關係
> 由 developer 在 **agent** 指定,不在 skill 內互連。

---

## 為什麼 stack skill 的核心職責是「版本錨點」(研究結論)

LLM 預設會生成**過時版本**的框架程式碼 —— 訓練資料是多版本混合、偏向最多人寫的舊版。
業界對策(`llms.txt` for sites、`LLMS.md` for repos)就是給模型一份 **curated、版本鎖定**
的 context 去覆寫 stale default。stack skill 在 gan-harness 裡就是這個角色。

證據(都是會咬人的版本 delta):

| Stack | 模型的 stale default | 該版本實際要求 |
|---|---|---|
| React 19 | `forwardRef` 包 ref、`useState`+`useEffect` 手刻表單狀態 | `ref` 是一般 prop;Actions + `useActionState`/`useFormStatus`/`useOptimistic` |
| Next.js 15 | 同步 `cookies()`/`headers()`、fetch 預設快取 | `await cookies()`/`headers()`/`params`;fetch 預設 `no-store` |
| Python 3.12+ | `TypeVar` + `Generic[T]` | PEP 695 `def f[T]()` / `type X = …` / `@override` |

→ **stack skill 不記版本,等於放任 agent 用舊版寫法。** 抓版本 + 強調 delta 是 creator 的職責。

---

## stack skill 到底該記錄哪些事(最終清單)

只記這 5 類,全部是「harness 或 agent **非知道不可、且模型不會自己知道**」的:

1. **Version pin** — 框架 / 語言 / 測試框架 / 少數版本敏感 dep 的確切版本。
2. **Version highlights** — 該版本**改變了寫法**、且模型預設會寫錯的幾條 delta(最高價值)。
3. **`## Commands`** — gate 契約(lint / typecheck / test 框架),三方共用。
4. **測試框架** — pytest / vitest / …(連同任何版本特定的 test API)。
5. **必 enforce 的 convention** — barrel idiom、lint-ignore、project layout(~5 行,非教學)。

**不記**:routing/auth/deployment 教學(那是 pattern skill)、`Related skills`(在 agent 指定)。

---

## 新的 stack skill 產出模板(creator Step 3 換成這個)

```markdown
---
name: <stack-name>
description: Use when a sprint touches <Stack Name> <major.minor> — <language, framework, test runner>. Carries the harness gate commands + the version-specific idioms that override the model's stale defaults. Required at contract time to shape the verification_plan.
---

# <Stack Name> <version>

Gate contract + **version anchor** for <Stack Name> **<pinned version>**. This file's
job: pin the version and flag what THIS version does differently, so code isn't written
to an older version's defaults. Implementation patterns live in separate pattern skills
(the developer wires which ones, in the agent — not here).

## Version (creator pins these at build time)

- <Framework>: **<x.y.z>** (released <date>)
- Language / runtime: **<x.y>**
- Test framework: **<name x.y>**
- Version-sensitive deps: **<dep x.y>** (only the few whose API changed by version)

## Version highlights (write to these — NOT the older defaults the model reaches for)

- **<feature>:** do `<new way>` — NOT `<the pre-version way>`.
- (React 19 example) **ref as prop:** pass `ref` directly — do NOT wrap in `forwardRef`.
- (React 19 example) **async form state:** `useActionState` / `useFormStatus` / `useOptimistic` + Actions — not manual `useState`+`useEffect`.
- (Next 15 example) **async request APIs:** `await cookies()` / `await headers()` / `await params` — the sync form is deprecated.
- (Next 15 example) **uncached by default:** fetch defaults to `no-store`; opt INTO caching explicitly.

## Commands
<!-- harness gate contract; pre-commit hook + evaluator both read this. {scope} substituted at call time. -->

| Key | Command |
|---|---|
| lint.fix | `<lint> --fix {scope}` |
| lint.check | `<lint> {scope}` |
| typecheck | `<typecheck> {scope}` |
| test.unit | `<test-runner> {scope}` |
| test.smoke | `<smoke-runner> {scope}` |   <!-- optional -->

## Conventions (only what the harness must enforce — ~5 lines, no tutorials)

- Test framework: <pytest | vitest | ...>
- Barrel / module idiom: <`__init__.py` | `index.ts` | `mod.rs`>
- Lint-ignore: <generated/vendored dirs the gate must skip>
```

**無 `## Related skills`、無 `references/`** —— 通常整個 stack skill 就一個 SKILL.md。
Version highlights 是新增的核心區塊;`## Commands` 保留(你強調的,每 stack 一套測試框架)。

---

## skill 之間的關係:在 agent 指定,不在 skill 內

你的決定:**skill 不自我宣告 `Related skills`。** 哪些 stack / pattern skill 相關、何時載,
由 developer 寫在 **agent 的 `## Your Skills` 索引**裡(就是 generator.thin.md 那段)。好處:
- 關係是**集中、可見**的(看一個 agent 就知道它用哪些 skill),不是散在 N 個 skill 裡。
- skill 保持**自包含、可移植** —— 換 agent 套用同一個 skill,不必改 skill 內的互連。
- 少一個會腐爛的面(skill A 改名,不必去 N 個 skill 改 `Related skills`)。

> 待你決定:pattern skill(如 `agentcore-browser-live-view`)目前也帶 `> Related skills:`。
> 要不要一致地拿掉、全部移到 agent 指定?我建議**一致拿掉**,但 pattern skill 是你手寫的
> POC 產物,你也可以選擇保留。先不動,等你定。

---

## creator process 怎麼改

| 舊 Step | 新做法 |
|---|---|
| Step 1 — capture intent(name / source / scope) | **改**:capture name + **target version**(必問,不可預設)+ test framework + lint/typecheck/test 指令 |
| — (新增) | **Step 1.5 — version research**:確認該版本相對前版的「改變寫法」delta(WebFetch 官方 release notes / upgrade guide),寫成 Version highlights。**這是 creator 的核心職責。** |
| Step 2 — vendor web docs(GitHub raw / 三層 fallback / provenance) | **刪除**。stack skill 不再 vendor doc 庫 |
| Step 2.5 — emit `## Commands` | **保留** |
| Step 2.6 — PBT support | 移出 → PBT 是 pattern skill / approach handbook |
| Step 3 — 寫 SKILL.md(大 references index) | 換成上面**輕量 + 版本錨點**模板 |
| Step 4 — 自驗 | 縮成:有 name+description;`## Commands` 四個 required key 都在且含 `{scope}`;**Version + highlights 非空** |
| Step 5 — handoff | 「patterns 之後用獨立 pattern skill 補;relationships 在 agent 指定;別塞回這裡」 |

creator 自身從 304 行縮到估 ~120 行(web-vendoring 整章消失,換進一個輕量 version-research 步驟)。
`references/commands-contract.md` 保留;`references/pbt-patterns.md` 移出當 pattern skill。

---

## 怎麼接回 agent template / discovery

- stack discovery(在 `harness-conventions`)不變:有 `## Commands` 的就是 stack skill。輕量化 + 加 Version 區塊**不影響 discovery**。
- pattern skill 無 `## Commands` → 被歸成「Skill tool 觸發才載」。
- agent 不靠 skill 內互連認識彼此 —— 一律由 agent 的 `## Your Skills` 索引(developer 指定)wire。

### Sources
- [llms.txt / LLMS.md — curated version context for LLMs](https://github.com/llmspec/llms-spec)
- [React 19 Upgrade Guide (ref as prop, forwardRef deprecated, Actions)](https://react.dev/blog/2024/04/25/react-19-upgrade-guide)
- [Next.js 15 — async request APIs + caching defaults](https://nextjs.org/docs/app/guides/upgrading/version-15)
