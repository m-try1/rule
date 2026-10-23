# rule

个人分流规则。**`Surge/*.list` 是唯一源，`Clash/*.yaml` 由 `build.py` 生成，不要手改。**

## 消费方

| 源 | 引用位置 |
| --- | --- |
| `Surge/*.list` | `internetconfig/Surge/Surge.conf:84-89`（RULE-SET）、`Loon/Loon-YToo.conf:90-95` |
| `Clash/*.yaml` | `internetconfig/Clash/Clash-ytoo.yaml:258-280`、`Clash-prpr.yaml:264-286`（经 `ghfast.top`） |

策略：`PersonalProxy`→Proxy，`PersonalDirect`→DIRECT，`PersonalReject`→REJECT，`Emby`→Emby。

## 改规则

只改 `Surge/<名字>.list`，然后：

```bash
./build.py           # 重新生成 Clash/*.yaml
./build.py --check   # 校验是否过期，过期 exit 1
git commit -am "..." && git push
```

push 后 Actions 自动跑 `build.py`，有差异就提交 `chore: regenerate Clash rules from Surge [skip ci]`。

## 验证 CI

```bash
gh run list --limit 3
gh run view <id> --log | grep -E "wrote|nothing to commit|files changed"
gh workflow run build.yml          # 手动触发
git log --oneline origin/main -3
```

`nothing to commit` 是正常结果。要测回写路径：故意推一个过期 `Clash/*.yaml` 再 `gh workflow run build.yml`，确认 bot 提交把它修正。

## 验证 Surge 生效

改完源文件 ≠ Surge 里生效，必须刷外部资源：

```bash
surge-cli external-resource update all          # 4 个规则集应为 [ruleset, remote, ready]
surge-cli rule match <domain>                   # 看命中的是哪个规则集
surge-cli rule temp list                        # 临时规则优先于 profile 规则
surge-cli dump rule-usage
```

- `external-resource update all` 里 `07a9ebd8d98ea2e2b54084580679a168`（YToo 订阅）长期 400，与本仓库无关。
- 证明新文件已加载：拿一条改变了匹配宽度的规则做子域探针（旧规则不命中子域、新规则命中）。

## 转换规则

| Surge | Clash |
| --- | --- |
| `DOMAIN,x,extended-matching` | `- DOMAIN,x` |
| `DOMAIN-SUFFIX,x,extended-matching` | `- DOMAIN-SUFFIX,x` |
| `IP-CIDR,x,no-resolve` | `- IP-CIDR,x,no-resolve` |

`extended-matching` / `pre-matching` 是 Surge 独有，丢弃；`no-resolve` 保留。注释与被注释的规则原样带过。
未知规则类型或选项直接 exit 2，不静默丢规则。支持类型见 `build.py:20` 的 `CLASH_TYPES`。

## build.py

Python 3 标准库，173 行，exit `0` 成功 / `1` 过期或无源文件 / `2` 无法转换。
不用 subconverter 是因为它丢注释，而中文分节注释是可读性的一部分。

## 更多

- [`docs/rule-notes.md`](docs/rule-notes.md) —— 实测定论
- [`docs/gotchas.md`](docs/gotchas.md) —— 踩过的坑
