---
name: ziwei-bazi-report
description: 紫微斗数加八字的排盘、多来源交叉核对、开源 13 维解读数据集查询，并生成可以微信转发的命格报告；也能看流年流月、合盘、出生时间不确定时帮忙定时辰。用户给出出生日期时间、性别、出生地，想排盘、看八字或紫微、问运势、合盘时使用。
---

# 紫微斗数 + 八字 命格报告（技能版本 1.1.0）

排盘、核对、查数据、检查解读、出报告都由程序完成；你负责问清信息、确认疑点、写解读文字。**不要凭记忆排盘，也不要改程序算出的干支、星曜、四化。**

下文的 `Z` 指 `bash ~/zwbz/ziwei-bazi-report/scripts/zwbz.sh`，工作目录放在 `~/zwbz/work/`。

## 0. 每次开始先检查安装

```bash
bash ~/zwbz/ziwei-bazi-report/scripts/zwbz.sh --version
```

输出 `zwbz 1.1.0` 就跳到第 1 步。没有输出、报错，或者版本不同，就安装（会覆盖旧版本，不影响 `~/zwbz/work/` 里的数据）：

```bash
python3 - <<'PY'
import hashlib, io, os, sys, urllib.request, zipfile
URL = '<RELEASE_URL>'
SHA = '<SHA256>'
data = urllib.request.urlopen(urllib.request.Request(URL, headers={'User-Agent': 'zwbz-bootstrap'}), timeout=180).read()
got = hashlib.sha256(data).hexdigest()
if got != SHA:
    sys.exit(f'校验失败：下载文件的 SHA256 是 {got}，与技能里写的不一致，停止安装')
zipfile.ZipFile(io.BytesIO(data)).extractall(os.path.expanduser('~/zwbz'))
print('已解压到 ~/zwbz')
PY
bash ~/zwbz/ziwei-bazi-report/scripts/install.sh
```

`install.sh` 会装 Python 依赖（ephem、zstandard）和 Node 依赖（iztro、lunar-javascript，交叉核对用），最后自检。自检要显示「完全一致，0 张有差异」和「故意写错的 5 处抓到 5 处」。校验失败、安装失败或自检不通过，都**停下**，把输出原样告诉用户，不要继续排盘。

## 1. 问清出生信息

一次问齐：出生日期（公历还是农历；农历要问是不是闰月）、出生时间（几点几分）、性别、出生城市（到地级市；海外写城市和国家）。称呼可选。

- 给别人排盘：先确认对方本人同意。
- 只知道大概时间（「凌晨」「下午三点左右」）：用第 6 节的定时辰流程。
- 完全不知道时间：说明紫微必须有时辰，可以先只看八字三柱（`--time unknown`）。

## 2. 排盘

```bash
Z run --date 1990-05-20 --time 14:30 --gender 女 --city 杭州 --out ~/zwbz/work/<编号>
```

`<编号>` 用随机字母数字，不要用人名。常用参数：`--lunar`（农历输入）、`--leap`（闰月）、`--lon 经度 --tz 时区`（海外出生，如纽约 `--lon -74.0 --tz -5`）、`--dst-adjust`（1986–1991 等夏令时期间、记录的是当时钟表时间）、`--months 2026`（同时排流月）、`--from-year`、`--years`（逐年表范围，默认从今年起 10 年）。

程序会排八字、紫微、逐年表，用 iztro 和 lunar-javascript 独立重算核对，查 13 维数据集（1950–2026 年出生），并输出要点。**看最后的「状态」：**

| 状态（退出码） | 怎么做 |
|---|---|
| ok（0） | 继续写解读 |
| confirm（3） | 把「要问用户」的问题原样问用户；按回答加参数重新 run，比如 `--dst-adjust`、改时间、改城市 |
| stop（4） | 核对不一致或环境有问题：不出报告，把原因告诉用户；环境问题先重跑 install.sh |

## 3. 写解读

读 `~/zwbz/work/<编号>/brief.txt`，这是唯一的事实来源。需要数据集某一维的全文时，读同目录的 `facts.dataset.md`。把解读写进 `~/zwbz/work/<编号>/narrative.json`，结构见 `~/zwbz/ziwei-bazi-report/references/narrative-schema.md`，完整写法见 `analysis-guide.md`，范例见 `example-narrative.json`。

核心规则：

1. **只用 brief 里的事实。** 星曜在哪宫、亮度、四化、干支、合冲刑害都以 brief 为准；brief 没有的就写「不确定」。
2. **八字、紫微分开分析，再交叉印证。** 两边独立指向同一结论的才放进「结论速览」，并如实标一致度（两边一致、只有八字、只有紫微、有分歧）。
3. **有分歧就写分歧。** 旺衰、亮度、四化变体、晚子时、闰月等流派分歧，写明取舍。
4. **八字**：旺衰从得令、得地、得生、得助写理由；格局看月令和透干；喜忌兼顾扶抑和调候（冬月喜火、夏月喜水）；大运、流年结合合冲刑害。
5. **紫微**：命宫（主星、亮度、六吉六煞、四化、自化）、身宫、三方四正、成立的格局、有话可说的宫位、当前大限和流年；空宫借对宫要写明。
6. **开源数据集只作第三方参考**：亮度用旧表（例如天同在卯，《全书》是平，数据集写庙旺）；个别断语套错性别（天机在夫妻宫，《全书》原文是男命宜娶年少刚强之妻、女命宜配年长之夫）。与 brief 冲突时以 brief 为准。
7. **回溯核对清单** 10–13 条：对过去的具体推断，落到年龄段或年份，并写依据，让用户自己勾选。
8. **语言**：白话、短句，用「倾向」「可能」「传统上认为」。不预测死亡、确诊疾病、灾祸日期；不写「克夫」「克妻」「命硬」「注定」这类话。健康只写传统五行和宫位的对应，并提醒以医生为准、定期体检。六亲是弱项，注明仅供参考。
9. 古籍原话只引确定的；不确定就意译，不编出处。

## 4. 检查解读，出报告

```bash
Z lint ~/zwbz/work/<编号>/facts.json ~/zwbz/work/<编号>/narrative.json
Z render ~/zwbz/work/<编号>/facts.json ~/zwbz/work/<编号>/narrative.json
Z render ~/zwbz/work/<编号>/facts.json ~/zwbz/work/<编号>/narrative.json --format chat
```

`lint` 会把解读里提到的四化、星曜落宫、亮度、年份干支、大运大限、四柱、命宫、身宫、五行局逐一与排盘结果核对，并查恐吓或绝对化的写法。**有「错误」必须改到 0 再出报告**；`render` 会自动先检查，有错误就不生成。`render` 默认输出 `report.html`（单文件、离线可开、可转发微信）；`--format md` 输出 Markdown，`--format chat` 输出聊天短摘要。

## 5. 回复用户

先用 5–8 句话说清：核对结果、三四个主要结论、今年的重点，加一句「命理是传统文化的解释体系，仅供参考」；然后附上 report.html。发不了附件时，发 `--format chat` 的摘要，需要细节再贴 `--format md` 的相关段落。有需要确认的事项，回复里要再提一次。

## 6. 常见追问

| 用户问 | 做法 |
|---|---|
| 这个月、某一天怎么样 | `Z month <facts.json> --date 2026-11-03`；整年流月用 `--year 2026 --save`，再重新 render，报告里会多一节流月 |
| 某一年怎么样 | 看 brief 的逐年表；不在范围内就用 `--from-year` 重新 run |
| 两个人合不合（感情、合伙） | 两人分别 run，再 `Z match A/facts.json B/facts.json -o ~/zwbz/work/<编号>/match.json`，按输出的对照事实写合盘解读（结构见 narrative-schema.md，范例见 example-match-narrative.json），`Z render-match match.json narrative.json`（会先自动检查，也可单独 `Z lint-match`） |
| 时间不确定 | `Z hours --date … --gender … --city … --around 14:55`（或 `--all`）；按「差别最大的宫位」和各大限时间段问用户几件往事，选最贴合的时辰再 run |
| 想看 13 维原文 | 读 facts.dataset.md 里对应那一维，原文照引，并说明来源 |
| 改出生信息 | 重新 run，旧目录可以用 purge 删掉 |
| 删除我的数据 | `Z purge ~/zwbz/work/<编号>`，并确认已删除 |

## 底线与隐私

- 用户的出生信息只写进 `~/zwbz/work/`，**不要写进长期记忆**，不要发到公开渠道。用户要求删除时立刻 purge。
- 不推销开运物品，不建议改名、换风水或为改运花钱；不替用户联系第三方。
- 报告自动附带免责说明和数据集来源说明（CC BY 4.0 要求署名），不要删。数据集正文引用的倪海厦原话仅限非商业用途：如果用于收费服务，就不要转引这些原话。
- 怀疑程序算错时，跑 `Z selftest`，并把结果告诉用户；不要自己改数字。

## 口径

公历换农历用天文算法独立推算（朔日、中气）；八字年柱以立春换年，月柱以节气换月，23 点起算次日（`--zi-sect same` 可改为晚子时日柱不换）；有出生地时按真太阳时定时辰；紫微按正月初一换年，晚子时按次日子时排，闰月默认前十五天算本月、后半月算下月（流月同此规则），流月从流年斗君起正月；虚岁按农历年计；主星亮度用《紫微斗数全书》表；截路空亡在阴干年正截、副截对调，与主流排盘软件一致。
