# 踩过的坑

## 把行为改变说成「修漂移」

`dns.alidns.com` / `doh.pub` 两边从 2025-03-26 的 `cb9296f` 起就一致地写成 Surge `DOMAIN`、
Clash `DOMAIN-SUFFIX`，**不是漂移**。我单边改成 `DOMAIN-SUFFIX` 并汇报为「修漂移」，
方向是任意选的——`build.py` 本来就支持把 Clash 改成 `- DOMAIN`、Surge 行为不变。

行为改变类改动先问，给并列选项和各自代价，汇报时区分「我选的」和「唯一做法」。

## 拿「当下有人先命中」当作「规则该删」

建议删 `alidns.com` / `doh.pub` 被驳回。这两条的目的是兜底防上游变动，
判断标准是能否独立成立，不是当下命中情况。

## 以为 `extended-matching` 是后缀

曾据此推断「`DOMAIN`→`DOMAIN-SUFFIX` 应该没差别」，与实测相反（见 `rule-notes.md`）。
不确定修饰符语义时，用一条**未改动的现有规则**做探针，输入要能区分两种假设（这里是子域）。

## 改完规则就以为生效

profile 从 raw.githubusercontent 拉规则集，`update-interval` 到期才重新拉。
不刷 `external-resource`，Surge 里跑的还是旧内容；`rule match` 命中的可能来自旧规则或别的规则集。

必须：① `surge-cli external-resource update all` 确认 `ready`；② 看命中的是**哪个规则集**；
③ 用改变了匹配宽度的规则做子域探针，区分「新文件生效」和「旧缓存恰好命中」。

## 忽略临时规则抢占 profile 规则

`relay.zedra.dev` 加进 `PersonalDirect.list:61` 后，`rule match` 命中的其实是用户自建的临时规则
`DOMAIN-SUFFIX,zedra.dev,DIRECT`——更宽、优先级更高。临时规则只在内存里，
`dump rule` 和 profile 文件都看不到。

排查「规则不生效」先跑 `surge-cli rule temp list`。汇报时要说明生效的是临时规则，
别让用户以为 profile 规则在起作用。

## CI 只跑过「无事可做」分支就以为验证过了

首次 push 后 Actions `success`，走的是 `nothing to commit` 分支，回写路径（`git commit` + `git push`）
一次都没执行——而权限、分支保护、非快进冲突恰好都在那里失败。

必须故意推一个过期 `Clash/*.yaml`，`gh workflow run build.yml` 触发，确认 bot 提交真的产生。
验证完整理：`git diff --quiet <改动前 sha> HEAD` 为零。同时确认没触发第二次运行（防自激循环，
`paths` 过滤 + `[skip ci]` 双重保险有效）。

## 在没核对的机器上下判断

汇报里写过「NUC 侧的 Clash 配置我没法核对是否还有别的引用点」——
`~/projects/internetconfig/Clash/` 只在 Mac 上存在，NUC 侧根本没有这个目录。
那句话暗示了一件不存在的事。查不到就不写，或明确写「未核对」，别给听起来合理的猜测。

## 源文件缺结尾换行

`c7548cc` 时 `Surge/Emby.list`、`Surge/PersonalDirect.list`、`Surge/PersonalReject.list` 三个文件
末尾都没有换行（`a892ffd` 已补）。往这种文件末尾追加内容会被拼接到最后一行规则的尾部，
形成非法规则，而且报错指向的位置和真实原因对不上。

追加前先查：`tail -c 1 <file> | xxd` 应为 `0a`。
