# 实测定论

本文件记录**已经实测确认**的结论。凡标注「实测」的都跑过命令、有观测；凡标注「未验证」的不得当作事实引用。

---

## `extended-matching` 不是后缀匹配

**实测日期**：2026-10-23

`extended-matching` 是让规则**额外**匹配 TLS SNI 和 HTTP Host header，用于客户端直连 IP、
拿不到请求域名（或请求目标与域名不一致）的场景。它**不提供后缀语义**。
后缀能力只来自 `DOMAIN-SUFFIX` 这个匹配类型本身。

实测反证（用仓库里未改动的规则做探针）：

```
surge-cli rule match neo.iflya321.com      # Emby.list 里是 DOMAIN,neo.iflya321.com,extended-matching
→ Matched: RULE-SET,…/Surge/Emby.list, Policy: Auto-0.2-YToo

surge-cli rule match x.neo.iflya321.com
→ Matched: FINAL,Final,dns-failed
```

若 `extended-matching` 带后缀语义，第二条应当命中 Emby。实际没有。

⇒ **别把 `DOMAIN,x,extended-matching` 当成后缀规则写**。要后缀就显式写 `DOMAIN-SUFFIX`。

---

## 查 Surge 实际在用哪个 DoH 端点

**实测日期**：2026-10-23

`surge-cli dump dns` 的每条缓存记录末尾都带 `From:` 字段，它就是该域名**本次解析实际走的上游**。
这是唯一能直接观测「实际生效的 DNS 上游」的入口。

当时的全量分布（179 条缓存）：

| `From:` | 条数 |
| --- | --- |
| `h3://613151-vkwgbxz3j9sqc1y4.alidns.com/dns-query` | 84 |
| `https://doh.pub/dns-query` | 83 |
| `fe80::5%en0` | 1 |
| `223.5.5.5` | 1 |

结论：阿里 DoH 的实际端点是 `613151-vkwgbxz3j9sqc1y4.alidns.com`
（与 `~/projects/internetconfig/Surge/Surge.conf:46` 的 `encrypted-dns-server` 一致），
**不是** `dns.alidns.com`。

命令细节：

- 子命令是 `dump dns`，写成 `dns dump` 会报 `Unknown command: dns dump`。
- `dump dns` 不在 `help dump` 的子命令列举里，但确实有效。
- DoH 连接本身**不进** `dump request` / `dump recent` 历史（是解析器内部行为），所以查「DoH 有没有走代理」不能靠请求列表，只能靠 `From:` 字段和 `rule match`。

---

## 为什么 DNS 兜底规则写 `alidns.com` 而不是 `dns.alidns.com`

**实测日期**：2026-10-23

| 域名 | 是 `dns.alidns.com` 子域 | 是 `alidns.com` 子域 |
| --- | --- | --- |
| `613151-vkwgbxz3j9sqc1y4.alidns.com`（**实际在用**） | ❌ | ✅ |

原来写的是 `DOMAIN,dns.alidns.com`，只能罩住 `dns.alidns.com` 自身及其子域，
**永远罩不住实际端点**。改成 `DOMAIN-SUFFIX,alidns.com` 后才真正覆盖。

改后实测：

```
surge-cli rule match 613151-vkwgbxz3j9sqc1y4.alidns.com
→ Matched: RULE-SET,…/Surge/PersonalDirect.list, Policy: DIRECT   （改前命中的是 ChinaNoMedia_All.list）
```

### 这两条为什么保留而不是删掉

`ChinaNoMedia_All.list` 里已经有 `DOMAIN-SUFFIX,alidns.com`、`DOMAIN-SUFFIX,doh.pub`，
所以**当下**不靠个人规则也是 DIRECT。但保留理由是用户明确要求：

> 还是要放在我的个人规则里的，避免别人更新了丢了

即：外部规则集哪天删了这两条，个人规则必须独立兜住。评价这类「兜底规则」的标准是
**它能否独立成立**，不是「当下有没有人先命中」。按这个标准，
`DOMAIN,dns.alidns.com` 是不成立的（罩不住实际端点），`DOMAIN-SUFFIX,alidns.com` 才成立。

优先级佐证：`Surge.conf:85` 的 `PersonalDirect` 排在 `Surge.conf:163` 的 `ChinaNoMedia` 之前，
个人规则优先生效。

副作用：`*.alidns.com` 整片现在都走 DIRECT。对 DNS 全家桶是合理范围，
但若将来要让某个 `alidns.com` 子域走代理，这条会抢先挡住。

---

## Emby 站的识别依据

**实测日期**：2026-10-23

用户要求核查 `test.28.al`、`neo.iflya321.com`、`st.stentvessel.xyz` 三个域名。
前两个已在 `Surge/Emby.list`，第三个缺失。判定 `test.28.al` 属同一 Emby 站群的依据：

1. `surge-cli dump request` 有 3 条 `test.28.al` 记录（SenPlayer，HTTPS + QUIC）。
2. 解析结果是 Cloudflare IP（`104.21.17.237`、`172.67.178.219`），
   与 `st.stentvessel.xyz`、`neo.iflya321.com` 同一 CDN 后面。
3. 访问客户端同为 `SenPlayer`，与既有 Emby 域名一致。
4. `dump traffic-stat-host` 里 `28.al` 有 7.2 MB 下行，量级与其他 Emby 站相当。

加规则时用 `DOMAIN`（不是 `DOMAIN-SUFFIX`），与 `Emby.list` 里其他三条保持一致，
避免误伤 `28.al` 下的其他站点。

---

## 规则集实际命中情况

**实测日期**：2026-10-23

```
surge-cli dump rule-usage
      16  RULE-SET,…/m-try1/rule/main/Surge/PersonalDirect.list
       3  RULE-SET,…/m-try1/rule/main/Surge/Emby.list
```

`PersonalDirect` 命中极少是正常的：它装的是家居设备、内网域名、DNS 上游这类低频目标。
命中数低**不是**「规则没用」的证据，别据此删规则。

---

## 未验证项

- **没有做过真实 Clash / mihomo 内核加载测试**（本机未装 mihomo 或 clash）。
  生成结果只验证到：合法 YAML（`ruby -ryaml` 可解析、`payload` 是字符串数组）、
  结构与 blackmatrix7 的 classical 规则集同构、逐条语义与 Surge 源一致。
  「Clash 客户端能正确加载」这一步没有实测证据。
- Loon 侧只确认了 `Loon/Loon-YToo.conf:90-95` 的引用路径与格式（直接用 Surge 格式），
  没有做 Loon 客户端加载实测。
