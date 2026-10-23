# rule

个人分流规则。**`Surge/*.list` 是唯一源**，`Clash/*.yaml` 由 `build.py` 自动生成，不要手改。

## 谁在用

| 文件 | 消费方 |
| --- | --- |
| `Surge/*.list` | `internetconfig` 的 `Surge/Surge.conf`（RULE-SET）、`Loon/Loon-YToo.conf`（Remote Rule，直接用 Surge 格式） |
| `Clash/*.yaml` | `internetconfig` 的 `Clash/Clash-ytoo.yaml`、`Clash/Clash-prpr.yaml`（rule-providers） |

`QuantumultX` 目前不引用这里的个人规则。

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

## 转换规则

| Surge | Clash |
| --- | --- |
| `DOMAIN,foo.com,extended-matching` | `- DOMAIN,foo.com` |
| `DOMAIN-SUFFIX,foo.com,extended-matching` | `- DOMAIN-SUFFIX,foo.com` |
| `IP-CIDR,1.2.3.4/32,no-resolve` | `- IP-CIDR,1.2.3.4/32,no-resolve` |

- `extended-matching`、`pre-matching` 是 Surge/Loon 独有，生成 Clash 时丢弃。
- `no-resolve` 两边都有，保留。
- 注释、空行、分节标题原样带过去。
- 遇到没有 Clash 对应物的规则类型或未知选项，`build.py` 直接报错退出（不静默丢规则）。

## 生成器

`build.py`，只依赖 Python 3 标准库。没用 subconverter 是因为它会丢掉全部注释，
而这里的中文分节注释是可读性的一部分。
