# 实测定论

## `extended-matching` 不是后缀匹配

`extended-matching` 只让规则**额外**匹配 TLS SNI 和 HTTP Host，不提供后缀语义。
后缀能力只来自 `DOMAIN-SUFFIX` 本身。

实测（用未改动的规则做探针，`Emby.list:8` 是 `DOMAIN,neo.iflya321.com,extended-matching`）：

```
surge-cli rule match neo.iflya321.com        → 命中 Emby.list
surge-cli rule match x.neo.iflya321.com      → 落到 FINAL
```

## 查 Surge 实际在用的 DoH 端点

`surge-cli dump dns` 每条缓存记录的 `From:` 字段就是该域名**本次实际走的上游**。

2026-10-23 全量分布（179 条）：`h3://613151-vkwgbxz3j9sqc1y4.alidns.com/dns-query` 84 条、
`https://doh.pub/dns-query` 83 条。即阿里 DoH 端点是 `613151-vkwgbxz3j9sqc1y4.alidns.com`，
不是 `dns.alidns.com`（与 `Surge.conf:46` 的 `encrypted-dns-server` 一致）。

命令细节：子命令写作 `dump dns`，`dns dump` 报 `Unknown command`。
DoH 连接本身不进 `dump request` 历史，查 DoH 走没走代理只能靠 `From:` 和 `rule match`。

## 为什么 DNS 兜底写 `alidns.com`

| 域名 | 是 `dns.alidns.com` 子域 | 是 `alidns.com` 子域 |
| --- | --- | --- |
| `613151-vkwgbxz3j9sqc1y4.alidns.com` | ❌ | ✅ |

原来写 `DOMAIN,dns.alidns.com`，罩不住实际端点。`PersonalDirect.list:18` 改成
`DOMAIN-SUFFIX,alidns.com` 后实测命中。

**这两条（`alidns.com`、`doh.pub`）为什么保留**：`ChinaNoMedia_All.list` 已覆盖它们，
当下不靠个人规则也是 DIRECT。保留理由是用户要求兜底防上游变动——外部规则集哪天删了，
个人规则必须独立罩住。判断标准是**能否独立成立**，不是当下有没有别处先命中。

副作用：`*.alidns.com` 整片走 DIRECT。将来若要让某个子域走代理，这条会抢先挡住。

## Emby 站群判定

`test.28.al` 归入 `Emby.list:14` 的依据：`dump request` 有 3 条记录（SenPlayer，HTTPS+QUIC）；
解析到 Cloudflare IP（`104.21.17.237`、`172.67.178.219`），与 `st.stentvessel.xyz`、
`neo.iflya321.com` 同一 CDN；`dump traffic-stat-host` 下行 7.2 MB 量级相当。
用 `DOMAIN` 而非 `DOMAIN-SUFFIX`，与同文件其他三条一致，避免误伤 `28.al` 下其他站点。

## 命中数低不代表规则没用

2026-10-23 `dump rule-usage`：`PersonalDirect.list` 17 次，`Emby.list` 3 次
（同期 `blackmatrix7/Direct.list` 140 次）。`PersonalDirect` 装的是家居设备、内网域名、
DNS 上游这类低频目标，命中数低是正常的。别据此删规则。

## 未验证

- **没有真实 Clash / mihomo 内核加载测试**（本机未装）。只验证到：`ruby -ryaml` 可解析、
  `payload` 是字符串数组、结构与 blackmatrix7 的 classical 规则集同构、逐条语义与 Surge 源一致。
- Loon 只确认了 `Loon/Loon-YToo.conf:90-95` 的引用路径与格式，没做客户端加载实测。
