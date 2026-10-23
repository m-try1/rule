# rule

个人分流规则。**`Surge/*.list` 是唯一源**，`Clash/*.yaml` 由 `build.py` 自动生成，不要手改。

## 谁在用

| 文件 | 消费方 |
| --- | --- |
| `Surge/*.list` | `internetconfig` 的 `Surge/Surge.conf:84-89`（RULE-SET）、`Loon/Loon-YToo.conf:90-95`（Remote Rule，直接用 Surge 格式） |
| `Clash/*.yaml` | `internetconfig` 的 `Clash/Clash-ytoo.yaml:258-280`、`Clash/Clash-prpr.yaml:264-286`（rule-providers，经 `ghfast.top` 拉 raw） |

`QuantumultX` 目前不引用这里的个人规则。

四个规则集及其在 Surge 里的策略：

| 文件 | 策略 |
| --- | --- |
| `Surge/PersonalProxy.list` | Proxy |
| `Surge/PersonalDirect.list` | DIRECT |
| `Surge/PersonalReject.list` | REJECT |
| `Surge/Emby.list` | Emby |

## 怎么改

1. 只改 `Surge/<名字>.list`，写法照现有格式：
   ```
   # 分节注释
   DOMAIN-SUFFIX,example.com,extended-matching
   IP-CIDR,1.2.3.4/32,no-resolve
   ```
   注释行里已被禁用的规则写成 `# DOMAIN,foo.com,extended-matching`，生成时同样会以注释形式保留。

2. 本地生成并检查结果：
   ```
   ./build.py           # 重写 Clash/*.yaml
   ./build.py --check   # 只校验，过期返回 1
   ```

3. `git commit` + `git push`。推上去后 GitHub Actions 会再跑一次 `build.py`，
   若 `Clash/` 与源不同就自动提交一个 `chore: regenerate Clash rules from Surge [skip ci]`。

> 生成流程不会回环：bot 提交只动 `Clash/`，而 workflow 的 `paths` 只监听 `Surge/`、`build.py` 和自身。

4. 推完确认 CI 和客户端生效，见下面两节。

## 确认 CI 跑得对不对

```bash
cd ~/projects/rule

gh run list --limit 3                      # 最近几次运行，看 conclusion
gh run list --limit 1 --json databaseId,status,conclusion,headSha,displayTitle
gh run view <run-id> --log | grep -E "wrote|already up to date|files changed"
gh run view <run-id> --log-failed          # 只看失败步骤（没失败则无输出）
gh workflow run build.yml                  # 手动触发（workflow_dispatch）
git fetch -q origin && git log --oneline origin/main -3
```

判读要点：

- `Clash/ already up to date, nothing to commit` 是**正常**结果 —— 说明本地已生成好，CI 无需补写。
- 只有出过 `[main <sha>] chore: regenerate Clash rules from Surge [skip ci]` 才是回写路径。
- `git log` 里若一次 push 只对应一次 run、bot 提交后没有第二次 run，说明防循环生效。
- 回写路径本身要验证时：故意把某个 `Clash/*.yaml` 改成过期内容并推送，然后 `gh workflow run build.yml`，
  确认 bot 提交把它修正回来。验证完 `git diff --quiet <改动前 sha> HEAD` 应为空。

## 确认 Surge 侧真的生效

**改完源文件 ≠ Surge 里生效**。profile 从 raw.githubusercontent 拉规则，要 push 之后刷外部资源。
`update-interval` 到期才会自动拉，否则手动刷：

```bash
surge-cli external-resource list                    # 看 4 个 m-try1/rule 是否 [ruleset, remote, ready]
surge-cli external-resource update all              # 刷全部
surge-cli external-resource update <key>            # 只刷一个（key 就是 list 里那串 hash）
surge-cli rule match <domain>                       # 命中哪条规则
surge-cli rule explain <domain>                     # 含决策路径、Final policy
surge-cli dump rule-usage                           # 每个规则集累计命中次数
surge-cli --check ~/projects/internetconfig/Surge/Surge.conf   # 离线校验 profile 语法
```

判读要点：

- `external-resource update all` 输出里出现非 `success` 的行就是失败。已知 `07a9ebd8d98ea2e2b54084580679a168`（YToo 订阅转换）长期返回 400，与本仓库无关。
- `rule match` 命中 `RULE-SET,…/m-try1/rule/main/Surge/<name>.list` 才算你的规则生效。
- **临时规则优先于 profile 规则**，`surge-cli rule temp list` 能看到。若某个域名命中临时规则，你新加的个人规则虽已加载但排不上号。
- 想证明「新文件真的加载了（不是旧缓存）」：挑一条本次改动改变了匹配宽度的规则做子域探针。例如 `dns.alidns.com` 从 `DOMAIN` 改成 `DOMAIN-SUFFIX,alidns.com` 后，`x.dns.alidns.com` 应当命中。

## 转换规则

| Surge | Clash |
| --- | --- |
| `DOMAIN,foo.com,extended-matching` | `- DOMAIN,foo.com` |
| `DOMAIN-SUFFIX,foo.com,extended-matching` | `- DOMAIN-SUFFIX,foo.com` |
| `IP-CIDR,1.2.3.4/32,no-resolve` | `- IP-CIDR,1.2.3.4/32,no-resolve` |

- `extended-matching`、`pre-matching` 是 Surge/Loon 独有，生成 Clash 时丢弃。
- `no-resolve` 两边都有，保留。
- 注释、空行、分节标题原样带过去；被注释掉的规则也转成 Clash 注释。
- 遇到没有 Clash 对应物的规则类型或未知选项，`build.py` 直接报错退出（不静默丢规则）。
- 已支持的 Clash 规则类型见 `build.py` 的 `CLASH_TYPES`。

## 生成器

`build.py`，只依赖 Python 3 标准库，约 160 行。没用 subconverter 是因为它会丢掉全部注释，
而这里的中文分节注释是可读性的一部分。

退出码：`0` 成功；`1` `--check` 发现过期；`2` 规则类型或选项无法转换。

## 更多

- [`docs/rule-notes.md`](docs/rule-notes.md) —— 实测定论（`extended-matching` 的真实语义、DoH 端点取证、兜底规则为什么这样写）
- [`docs/gotchas.md`](docs/gotchas.md) —— 踩过的坑与错误做法
