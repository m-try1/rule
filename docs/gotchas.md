# 踩过的坑

本文件记录**做错过的做法**，按「症状 → 原因 → 正确做法」写。目的是别重复犯错。

---

## 把行为改变包装成「修漂移」

**症状**：发现 `Surge/PersonalDirect.list` 里写 `DOMAIN,dns.alidns.com`、
`Clash/PersonalDirect.yaml` 里写 `- DOMAIN-SUFFIX,dns.alidns.com`，
于是一边倒改成 `DOMAIN-SUFFIX`，并向用户汇报为「修漂移」。

**问题**：

1. 两边从 2025-03-26 的原始提交 `cb9296f` 起就不一致，**不是漂移**。
2. 方向是任意选的。`build.py` 本来就支持 `DOMAIN` → `- DOMAIN`，
   完全可以反过来把 Clash 改成精确匹配、Surge 行为不变。选了会改 Surge 线上行为的那一侧。
3. 「修漂移」暗示这是技术必然，实际是需要用户拍板的选择。

**正确做法**：行为改变类改动**先问**。给并列选项和各自代价，不替用户决定方向。
汇报时区分「这是我选的」和「这是唯一的做法」。

---

## 拿「当下有人先命中」当作「规则该删」

**症状**：查到 `alidns.com` 和 `doh.pub` 都已被 `ChinaNoMedia_All.list` 覆盖，
于是建议删掉个人规则里的这两条，理由是「已实测是死规则」。

**问题**：用户保留这两条的目的是**兜底防上游变动**。外部规则集哪天删了，
个人规则必须独立罩住。判断这类规则的标准是「它能否独立成立」，
不是「现在有没有别的规则先命中它」。

**正确做法**：先问这条规则的存在目的是什么，再评价它。兜底性质的内容不按当下的命中情况取舍。

---

## 以为 `extended-matching` 是后缀

**症状**：推测 `DOMAIN,x,extended-matching` 可能已经具备后缀语义，
因此「把 `DOMAIN` 改成 `DOMAIN-SUFFIX` 应该没有实际差别」。

**实际**：`extended-matching` 只管额外匹配 TLS SNI 和 HTTP Host，**不提供后缀**。
实测反证见 `docs/rule-notes.md`。

**正确做法**：不确定某个规则修饰符的语义时，用一个**未改动的现有规则**做探针实测，
而不是凭印象推断。探针要用「能区分两种假设」的输入（这里是子域）。

---

## 在 Surge 里改完规则就以为生效

**症状**：把新规则 push 上去，然后 `surge-cli rule match` 一看命中就宣布完成。

**问题**：profile 从 raw.githubusercontent 拉规则集，`update-interval` 到期才自动拉。
不刷外部资源，Surge 里跑的还是旧内容；`rule match` 命中可能来自旧规则或别的规则集。

**正确做法**：

1. 先 `surge-cli external-resource update all`，确认 4 个规则集都是 `[ruleset, remote, ready]`。
2. `surge-cli rule match` 的结果要看**命中的是哪个规则集**，只看到「命中某条规则」不够。
3. 要证明「新文件真的加载了」，挑一条本次改变了匹配宽度的规则做子域探针 ——
   旧规则不会命中子域、新规则会，这样能区分「新文件生效」和「旧缓存/别的规则集恰好命中」。

---

## 忽略临时规则会抢占 profile 规则

**症状**：新加的 `DOMAIN-SUFFIX,relay.zedra.dev` 明明在规则表里，
但 `rule match relay.zedra.dev` 显示命中的是 `DOMAIN-SUFFIX,zedra.dev,DIRECT`。

**原因**：`surge-cli rule temp list` 里有用户自建的临时规则 `DOMAIN-SUFFIX,zedra.dev,DIRECT`，
范围更宽、优先级更高，抢在新规则前面。临时规则只活在本机内存，`dump rule` 里看不到，
也不在任何 profile 文件里。

**正确做法**：

- 排查「规则不生效」时先跑 `surge-cli rule temp list`，别只看 profile。
- 临时规则优先级高于 profile 规则，宽规则会盖住窄规则。
- 汇报时要说明「当前生效的是临时规则，profile 里的这条已加载但排不上号」，
  不要让用户以为 profile 规则在起作用。

---

## 默认 CI 只跑过「无事可做」分支就以为验证过了

**症状**：push 后看到 Actions `success`，就宣布自动化可用。

**问题**：第一次运行走的是 `Clash/ already up to date, nothing to commit` 分支 ——
回写路径（`git commit` + `git push`）**一次都没执行过**。这条路径才是最容易坏的
（权限不足、分支保护、非快进冲突都会在这里失败）。

**正确做法**：故意把某个 `Clash/*.yaml` 改成过期内容推上去，
再 `gh workflow run build.yml` 触发，确认 bot 提交真的产生并推回。
验证完用 `git diff --quiet <改动前 sha> HEAD` 确认净内容为零。

另外要确认同一次变更**没有触发第二次运行**（防自激循环）。
2026-10-23 实测：`paths` 过滤 + `[skip ci]` 双重保险有效，一次 push 只对应一次 run。

---

## 在没核对的机器上作判断

**症状**：汇报里写「NUC 侧的 Clash 配置我没法核对是否还有别的引用点」。

**问题**：`~/projects/internetconfig/Clash/` 只在 Mac 上存在，NUC 侧根本没有这个目录。
那句话暗示了一件不存在的事，属于凭印象补事实。

**正确做法**：不确定某台机器上有没有某个目录时，先查再说；不能查就不写，
或者明确写「未核对」，而不是给出一个听起来合理的猜测。

---

## 改多个文件时忽略了「无结尾换行」的拼接触发

**症状**：往 `Surge/*.list` 末尾追加一行做测试，新增的规则报「未知选项」错误，
但一眼看不出原因。

**原因**：文件结尾没有换行符，追加内容被拼接到最后一行规则的尾部，形成非法规则。

**正确做法**：

- `Surge/*.list` 结尾一律保留换行（本仓库曾有三条 list 缺结尾换行，2026-10-23 已补）。
- 用脚本追加内容前先检查 `tail -c 1 <file> | xxd` 是否为 `0a`。
